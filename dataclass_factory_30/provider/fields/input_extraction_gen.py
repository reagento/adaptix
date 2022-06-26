import contextlib
from collections import deque
from copy import copy
from typing import Dict, Set, Optional, Mapping

from .crown_definitions import (
    InpDictCrown, InpListCrown, InpFieldCrown, InpCrown,
    ExtraForbid, ExtraCollect, RootInpCrown, FldPathElem, Path, InpNoneCrown,
)
from .definitions import InputExtractionGen, VarBinder, InputFigure, ExtraTargets
from ...code_tools import CodeBuilder, ContextNamespace
from ...common import Parser
from ...provider.definitions import (
    NoRequiredFieldsError, NoRequiredItemsError, ExtraFieldsError,
    ExtraItemsError, TypeParseError, ParseError
)
from ...provider.request_cls import InputFieldRM


class GenState:
    KNOWN_FIELDS = 'known_fields'

    def __init__(self, binder: VarBinder, ctx_namespace: ContextNamespace, name_to_field: Dict[str, InputFieldRM]):
        self.binder = binder
        self.ctx_namespace = ctx_namespace
        self._name_to_field = name_to_field

        self.field_name2path: Dict[str, Path] = {}
        self.path2suffix: Dict[Path, str] = {}
        self.path2known_fields: Dict[Path, Set[str]] = {}

        self._last_path_idx = 0
        self._path: Path = ()
        self._parent_path: Optional[Path] = None

    def _get_path_idx(self, path: Path) -> str:
        try:
            return self.path2suffix[path]
        except KeyError:
            self._last_path_idx += 1
            suffix = str(self._last_path_idx)
            self.path2suffix[path] = suffix
            return suffix

    def get_data_var_name(self) -> str:
        if not self._path:
            return self.binder.data
        return self.binder.data + '_' + self._get_path_idx(self._path)

    def get_known_fields_var_name(self) -> str:
        if not self._path:
            return self.KNOWN_FIELDS

        return self.KNOWN_FIELDS + '_' + self._get_path_idx(self._path)

    def get_extra_var_name(self) -> str:
        if not self._path:
            return self.binder.extra

        return self.binder.extra + '_' + self._get_path_idx(self._path)

    def field_parser(self, field_name: str) -> str:
        return f"parser_{field_name}"

    def raw_field(self, field: InputFieldRM) -> str:
        return f"r_{field.name}"

    @property
    def path(self):
        return self._path

    @contextlib.contextmanager
    def add_key(self, key: FldPathElem):
        past = self._path
        past_parent = self._parent_path

        self._parent_path = self._path
        self._path += (key,)
        yield
        self._path = past
        self._parent_path = past_parent

    def get_field(self, crown: InpFieldCrown) -> InputFieldRM:
        self.field_name2path[crown.name] = self._path
        return self._name_to_field[crown.name]

    def with_parent_path(self) -> "GenState":
        if self._parent_path is None:
            raise ValueError

        cp = copy(self)
        cp._path = self._parent_path
        cp._parent_path = None
        return cp


class BuiltinInputExtractionGen(InputExtractionGen):
    """BuiltinInputExtractionGen generates code that extracts raw values from input data,
    calls parsers and stores results at variables.
    """

    def __init__(
        self,
        figure: InputFigure,
        crown: RootInpCrown,
        debug_path: bool,
        strict_coercion: bool,
    ):
        self._figure = figure
        self._root_crown = crown
        self._debug_path = debug_path
        self._strict_coercion = strict_coercion
        self._name_to_field: Dict[str, InputFieldRM] = {
            field.name: field for field in self._figure.fields
        }

    def _is_extra_target(self, field: InputFieldRM):
        return (
            isinstance(self._figure.extra, ExtraTargets)
            and
            field.name in self._figure.extra.fields
        )

    def _create_state(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> GenState:
        return GenState(binder, ctx_namespace, self._name_to_field)

    def generate_input_extraction(
        self,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field_parsers: Mapping[str, Parser],
    ) -> CodeBuilder:
        for exception in [
            ExtraFieldsError, ExtraItemsError,
            TypeParseError, NoRequiredFieldsError,
            ParseError
        ]:
            ctx_namespace.add(exception.__name__, exception)

        crown_builder = CodeBuilder()
        state = self._create_state(binder, ctx_namespace)

        for field_name, parser in field_parsers.items():
            state.ctx_namespace.add(state.field_parser(field_name), parser)

        if not self._gen_root_crown_dispatch(crown_builder, state, self._root_crown):
            raise TypeError

        has_opt_fields = any(
            fld.is_optional and not self._is_extra_target(fld)
            for fld in self._figure.fields
        )

        builder = CodeBuilder()

        if has_opt_fields:
            builder += f"{binder.opt_fields} = {{}}"

        self._gen_header(builder, state)

        builder.extend(crown_builder)

        self._gen_extra_targets_assigment(builder, state)

        return builder

    def _gen_header(self, builder: CodeBuilder, state: GenState):
        if state.path2suffix:
            builder += "# suffix to path"
            for path, suffix in state.path2suffix.items():
                builder += f"# {suffix} -> {list(path)}"

            builder.empty_line()

        if state.field_name2path:
            builder += "# field to path"
            for f_name, path in state.field_name2path.items():
                builder += f"# {f_name} -> {list(path)}"

            builder.empty_line()

    def _gen_root_crown_dispatch(self, builder: CodeBuilder, state: GenState, crown: InpCrown):
        """Returns True if code is generated"""
        if isinstance(crown, InpDictCrown):
            self._gen_dict_crown(builder, state, crown)
        elif isinstance(crown, InpListCrown):
            self._gen_list_crown(builder, state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, builder: CodeBuilder, state: GenState, sub_crown: InpCrown, key: FldPathElem):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(builder, state, sub_crown):
                return
            if isinstance(sub_crown, InpFieldCrown):
                self._gen_field_crown(builder, state, sub_crown)
                return
            if isinstance(sub_crown, InpNoneCrown):
                self._gen_none_crown(builder, state, sub_crown)
                return

            raise TypeError

    def _get_path_literal(self, path: Path) -> str:
        return repr(deque(path)) if self._debug_path and len(path) > 0 else ""

    def _gen_var_assigment_from_data(
        self,
        builder: CodeBuilder,
        state: GenState,
        *,
        assign_to: str,
        ignore_lookup_error=False
    ):
        last_path_el = state.path[-1]
        parent_state = state.with_parent_path()
        before_path = parent_state.path

        if isinstance(last_path_el, str):
            error = KeyError.__name__
            parse_error = NoRequiredFieldsError.__name__
        else:
            error = IndexError.__name__
            parse_error = NoRequiredItemsError.__name__

        path_lit = self._get_path_literal(before_path)
        data = parent_state.get_data_var_name()
        last_path_el = repr(last_path_el)

        if ignore_lookup_error:
            on_error = "pass"
        else:
            on_error = f"raise {parse_error}([{last_path_el}], {path_lit})"

        builder(
            f"""
            try:
                {assign_to} = {data}[{last_path_el}]
            except {error}:
                {on_error}
            """,
        )

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: InpDictCrown):
        known_fields = state.get_known_fields_var_name()

        if crown.extra in (ExtraForbid(), ExtraCollect()):
            state.ctx_namespace.add(known_fields, set(crown.map.keys()))

        data = state.get_data_var_name()
        extra = state.get_extra_var_name()
        path_lit = self._get_path_literal(state.path)

        if state.path:
            self._gen_var_assigment_from_data(
                builder, state, assign_to=state.get_data_var_name(),
            )
            builder.empty_line()

        builder += f"""
            if not isinstance({data}, dict):
                raise TypeParseError(dict, {path_lit})
        """

        builder.empty_line()

        if crown.extra == ExtraForbid():
            builder += f"""
                {extra} = set({data}) - {known_fields}
                if {extra}:
                    raise ExtraFieldsError({extra}, {path_lit})
            """
            builder.empty_line()

        elif crown.extra == ExtraCollect():
            builder += f"""
                {extra} = {{}}
                for key in set({data}) - {known_fields}:
                    {extra}[key] = {data}[key]
            """
            builder.empty_line()

        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: InpListCrown):
        data = state.get_data_var_name()
        path_lit = self._get_path_literal(state.path)
        list_len = str(crown.list_len)

        if state.path:
            self._gen_var_assigment_from_data(
                builder, state, assign_to=state.get_data_var_name(),
            )
            builder.empty_line()

        builder += f"""
            if not isinstance({data}, list):
                raise TypeParseError(list, {path_lit})
        """

        builder.empty_line()

        if crown.extra == ExtraForbid():
            builder += f"""
                if len({data}) > {list_len}:
                    raise ExtraItemsError({list_len}, {path_lit})
            """
            builder.empty_line()

        for key, value in enumerate(crown.map):
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_field_crown(self, builder: CodeBuilder, state: GenState, crown: InpFieldCrown):
        field = state.get_field(crown)

        if field.is_required:
            field_left_value = state.binder.field(field)
        else:
            field_left_value = f"{state.binder.opt_fields}[{field.name!r}]"

        self._gen_var_assigment_from_data(
            builder,
            state,
            assign_to=state.raw_field(field),
            ignore_lookup_error=field.is_optional,
        )
        data_for_parser = state.raw_field(field)

        if field.is_required:
            builder.empty_line()
            self._gen_field_assigment(
                builder,
                field_left_value,
                field.name,
                data_for_parser,
                state,
            )
        else:
            with builder("else:"):
                self._gen_field_assigment(
                    builder,
                    field_left_value,
                    field.name,
                    data_for_parser,
                    state,
                )

        builder.empty_line()

    def _gen_field_assigment(
        self,
        builder: CodeBuilder,
        field_left_value: str,
        field_name: str,
        data_for_parser: str,
        state: GenState,
    ):
        field_parser = state.field_parser(field_name)

        if self._debug_path and state.path:
            last_path_el = repr(state.path[-1])

            builder(
                f"""
                try:
                    {field_left_value} = {field_parser}({data_for_parser})
                except ParseError as e:
                    e.append_path({last_path_el})
                    raise e
                """
            )
        else:
            builder(
                f"{field_left_value} = {field_parser}({data_for_parser})"
            )

    def _gen_extra_targets_assigment(self, builder: CodeBuilder, state: GenState):
        # Saturate extra targets with data.
        # If extra data is not collected, parser of required field will get empty dict
        if not isinstance(self._figure.extra, ExtraTargets):
            return

        if self._root_crown.extra == ExtraCollect():
            for target in self._figure.extra.fields:
                field = self._name_to_field[target]

                self._gen_field_assigment(
                    builder,
                    field_left_value=state.binder.field(field),
                    field_name=target,
                    data_for_parser=state.get_extra_var_name(),
                    state=state,
                )
        else:
            for target in self._figure.extra.fields:
                field = self._name_to_field[target]

                if field.is_required:
                    self._gen_field_assigment(
                        builder,
                        field_left_value=state.binder.field(field),
                        field_name=target,
                        data_for_parser="{}",
                        state=state,
                    )

        builder.empty_line()

    def _gen_none_crown(self, builder: CodeBuilder, state: GenState, crown: InpNoneCrown):
        pass
