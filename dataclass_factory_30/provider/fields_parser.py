import contextlib
from collections import deque
from typing import Dict, Tuple, Set

from .definitions import PathElement, NoRequiredFieldsError, NoRequiredItemsError
from .essential import Mediator, CannotProvide
from .fields_basics import (
    ExtraForbid, ExtraCollect,
    InputFieldsFigure,
    RootCrown, Crown,
    DictCrown, ListCrown, FieldCrown,
    InputFFRequest, RootCrownRequest, ExtraKwargs, ExtraTargets,
)
from .provider_template import ParserProvider
from .request_cls import InputFieldRM
from .request_cls import ParserRequest, ParserFieldRequest
from ..code_tools import CodeBuilder, ClosureCompiler, BasicClosureCompiler
from ..common import Parser

Path = Tuple[PathElement, ...]


class GenState:
    def __init__(self, figure: InputFieldsFigure):
        self._name2field: Dict[str, InputFieldRM] = {
            field.field_name: field for field in figure.fields
        }
        self.field_name2path: Dict[str, Path] = {}
        self.path2suffix: Dict[Path, str] = {}
        self.path2known_fields: Dict[Path, Set[str]] = {}

        self._path_idx = 0
        self._path: Path = ()

    def _get_path_suffix(self, path: Path) -> str:
        try:
            return self.path2suffix[path]
        except KeyError:
            self._path_idx += 1
            suffix = str(self._path_idx)
            self.path2suffix[path] = suffix
            return suffix

    def _get_var_name(self, base: str, path: Path):
        if not path:
            return base
        return base + "_" + self._get_path_suffix(path)

    def get_data_var_name(self):
        return self._get_var_name("data", self._path)

    def get_extra_var_name(self):
        return self._get_var_name("extra", self._path)

    def get_known_fields_var_name(self, path=None):
        if path is None:
            path = self._path
        return self._get_var_name("known_fields", path)

    def get_field_parser_var_name(self, field_name: str) -> str:
        return f"parser_{field_name}"

    def get_field_var_name(self, field: InputFieldRM) -> str:
        return f"f_{field.field_name}"

    def get_opt_fields_var_name(self) -> str:
        return "opt_fields"

    def get_field_var(self, field_name: str) -> str:
        return f"f_{field_name}"

    def get_raw_field_var(self, field_name: str) -> str:
        return f"rf_{field_name}"

    def get_field(self, crown: FieldCrown) -> InputFieldRM:
        if crown.name in self.field_name2path:
            raise ValueError(f"{crown} appears twice")

        self.field_name2path[crown.name] = self._path
        return self._name2field[crown.name]

    @property
    def path(self):
        return self._path

    @contextlib.contextmanager
    def add_key(self, key: PathElement):
        past = self._path
        self._path += (key,)
        yield
        self._path = past


class FieldsParserGenerator:
    def __init__(
        self,
        figure: InputFieldsFigure,
        debug_path: bool,
        strict_coercion: bool,
    ):
        self.debug_path = debug_path
        self.strict_coercion = strict_coercion
        self.figure = figure

    def _gen_header(self, builder: CodeBuilder, state: GenState):
        for path, suffix in state.path2suffix.items():
            builder += f"""
                # {suffix} -> {list(path)}
            """

        builder.empty_line()

        for f_name, path in state.field_name2path.items():
            builder += f"""
                # {f_name} -> {list(path)}
            """

        builder.empty_line()

    def _create_state(self):
        return GenState(self.figure)

    def generate(
        self,
        compiler: ClosureCompiler,
        field_parsers: Dict[str, Parser],
        crown: RootCrown
    ) -> Parser:
        state = self._create_state()

        parser_body_builder = self._gen_parser_body(crown, state)

        builder = CodeBuilder()

        # copy global variables to local namespace capturing it's by closure
        self._gen_global_to_local(
            builder,
            {'constructor': 'g_constructor'},
            {
                state.get_known_fields_var_name(path): repr(known_fields)
                for path, known_fields in state.path2known_fields.items()
            },
            {
                f'g_{var}': var
                for var in (
                    state.get_field_parser_var_name(field_name)
                    for field_name in field_parsers
                )
            },
        )

        builder.empty_line()

        builder(
            "def fields_parser($data):",
            data=state.get_data_var_name()
        )
        with builder:
            builder.extend(parser_body_builder)

        builder += "return fields_parser"

        return compiler.compile(
            builder,
            "fields_parser",
            {
                "g_constructor": self.figure.constructor,
                **{
                    "g_" + state.get_field_parser_var_name(field_name): parser
                    for field_name, parser in field_parsers.items()
                },
            },
        )

    def _gen_global_to_local(self, builder: CodeBuilder, *local_to_global_vars: Dict[str, str]):
        for local_to_global in local_to_global_vars:
            for l_var, g_var in local_to_global.items():
                builder(
                    "$l_val = $g_var",
                    g_var=g_var,
                    l_val=l_var,
                )

    def _gen_parser_body(self, root_crown: RootCrown, state: GenState) -> CodeBuilder:
        crown_builder = CodeBuilder()
        if not self._gen_root_crown_dispatch(crown_builder, state, root_crown):
            raise ValueError

        builder = CodeBuilder()
        self._gen_header(builder, state)

        has_opt_fields = any(not f.is_required for f in self.figure.fields)

        if has_opt_fields:
            builder(
                "$opt_fields = {}",
                opt_fields=state.get_opt_fields_var_name(),
            )

        builder.extend(crown_builder)

        if isinstance(self.figure.extra, ExtraTargets) and root_crown.extra == ExtraCollect():
            targets = self.figure.extra.fields

            for target in targets:
                self._gen_field_assigment(
                    builder,
                    field_left_value=target,
                    field_name=target,
                    data_for_parser=state.get_extra_var_name(),
                    state=state,
                )

        builder += """
            return constructor(
        """

        with builder:
            for field in self.figure.fields:
                self._gen_field_passing(builder, state, field)

            if has_opt_fields:
                builder(
                    "**$opt_fields,",
                    opt_fields=state.get_opt_fields_var_name(),
                )

            if (
                root_crown.extra == ExtraCollect()
                and
                self.figure.extra == ExtraKwargs()
            ):
                builder(
                    "**$extra",
                    extra=state.get_extra_var_name(),
                )

        builder += ")"

        return builder

    def _field_is_extra_target(self, field: InputFieldRM):
        return (
            isinstance(self.figure.extra, ExtraTargets)
            and
            field.field_name in self.figure.extra.fields
        )

    def _gen_field_passing(self, builder: CodeBuilder, state: GenState, field: InputFieldRM):
        if field.is_required or self._field_is_extra_target(field):
            builder(
                "$var,",
                var=state.get_field_var(field.field_name),
            )
        else:
            builder(
                "$param=$var,",
                param=field.field_name,
                var=state.get_field_var(field.field_name),
            )

    def _gen_root_crown_dispatch(self, builder: CodeBuilder, state: GenState, crown: Crown):
        """Returns True if code is generated"""
        if isinstance(crown, DictCrown):
            self._gen_dict_crown(builder, state, crown)
        elif isinstance(crown, ListCrown):
            self._gen_list_crown(builder, state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, builder: CodeBuilder, state: GenState, sub_crown: Crown, key: PathElement):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(builder, state, sub_crown):
                return
            if isinstance(sub_crown, FieldCrown):
                self._gen_field_crown(builder, state, sub_crown)
                return
            if sub_crown is None:
                return

            raise ValueError

    def _get_path_lit(self, path: Path) -> str:
        return repr(deque(path)) if self.debug_path and len(path) > 0 else ""

    def _get_lookup_error(self, key: PathElement) -> str:
        return KeyError.__name__ if isinstance(key, str) else IndexError.__name__

    def _gen_var_assigment_from_data(self, builder: CodeBuilder, state: GenState, var: str):
        last_path_el = state.path[-1]
        before_path = state.path[:-1]
        error = self._get_lookup_error(last_path_el)

        if isinstance(last_path_el, str):
            parse_error = NoRequiredFieldsError.__name__
        else:
            parse_error = NoRequiredItemsError.__name__

        path_lit = self._get_path_lit(before_path)

        builder(
            """
            try:
                $var = $data[$last_path_el]
            except $error:
                raise $parse_error([$last_path_el], $path_lit)
            """,
            data=state.get_data_var_name(),
            var=var,
            error=error,
            parse_error=parse_error,
            path_lit=path_lit,
            last_path_el=repr(last_path_el)
        )

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: DictCrown):
        known_fields = set(crown.map.keys())
        state.path2known_fields[state.path] = known_fields

        with builder.context(
            known_fields=state.get_known_fields_var_name(),
            data=state.get_data_var_name(),
            extra=state.get_extra_var_name(),
            path_lit=self._get_path_lit(state.path),
        ):
            if state.path:
                self._gen_var_assigment_from_data(
                    builder, state, state.get_data_var_name(),
                )
                builder.empty_line()

            builder += """
                if not isinstance($data, dict):
                    raise TypeParseError(dict, $path_lit)
            """

            builder.empty_line()

            if crown.extra == ExtraForbid():
                builder += """
                    $extra = set($data) - $known_fields
                    if $extra:
                        raise ExtraFieldsError($extra, $path_lit)
                """

            elif crown.extra == ExtraCollect():
                builder += """
                    $extra = {}
                    for key in set($data) - $known_fields:
                        $extra[key] = $data[key]
                """

        builder.empty_line()

        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: ListCrown):
        with builder.context(
            data=state.get_data_var_name(),
            path_lit=self._get_path_lit(state.path),
            list_len=str(crown.list_len),
        ):
            if state.path:
                self._gen_var_assigment_from_data(
                    builder, state, state.get_data_var_name(),
                )
                builder.empty_line()

            builder += """
                if not isinstance($data, list):
                    raise TypeParseError(list, $path_lit)
            """

            builder.empty_line()

            if crown.extra == ExtraForbid():
                builder += """
                    if len($data) > $list_len:
                        raise ExtraItemsError($list_len, $path_lit)
                """

        builder.empty_line()

        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_field_crown(self, builder: CodeBuilder, state: GenState, crown: FieldCrown):
        field = state.get_field(crown)

        if self._field_is_extra_target(field):
            raise ValueError(
                "Field can not be extra target and be presented in crown"
            )

        if field.is_required:
            field_left_value = state.get_field_var(field.field_name)
        else:
            field_left_value = builder.fmt(
                '$opt_fields["$field_var"]',
                field_var=state.get_field_var(crown.name),
                opt_fields=state.get_opt_fields_var_name(),
            )

        self._gen_var_assigment_from_data(
            builder,
            state,
            state.get_raw_field_var(crown.name),
        )
        builder.empty_line()

        data_for_parser = state.get_raw_field_var(field.field_name)

        if field.is_required:
            self._gen_field_assigment(
                builder,
                field_left_value,
                field.field_name,
                data_for_parser,
                state,
            )
        else:
            builder("else:")
            with builder:
                self._gen_field_assigment(
                    builder,
                    field_left_value,
                    field.field_name,
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
        with builder.context(
            field_left_value=field_left_value,
            field_parser=state.get_field_parser_var_name(field_name),
            data_for_parser=data_for_parser,
        ):
            if self.debug_path:
                builder(
                    """
                    try:
                        $field_left_value = $field_parser($data_for_parser)
                    except ParseError as e:
                        e.append_path($last_path_el)
                        raise e
                    """,
                    last_path_el=repr(state.path[-1]),
                )
            else:
                builder += """
                    $field = $field_parser($raw_field)
                """


class FieldsParserProvider(ParserProvider):
    def _create_parser_generator(self, figure: InputFieldsFigure, request: ParserRequest):
        return FieldsParserGenerator(
            figure=figure,
            debug_path=request.debug_path,
            strict_coercion=request.strict_coercion,
        )

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        figure: InputFieldsFigure = mediator.provide(InputFFRequest(request.type))
        crown: RootCrown = mediator.provide(RootCrownRequest(request.type))

        if crown.extra == ExtraCollect() and figure.extra is None:
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if figure does not take extra data"
            )

        generator = self._create_parser_generator(figure, request)

        fields_parser = {
            field.field_name: mediator.provide(
                ParserFieldRequest(
                    type=request.type,
                    strict_coercion=request.strict_coercion,
                    debug_path=request.debug_path,
                    default=field.default,
                    is_required=field.is_required,
                    metadata=field.metadata,
                    field_name=field.field_name,
                    param_kind=field.param_kind,
                )
            )
            for field in figure.fields
        }

        parser = generator.generate(
            BasicClosureCompiler(),
            fields_parser,
            crown,
        )

        return parser
