import collections.abc
import contextlib
from typing import Dict, List, Mapping, Optional, Set

from ...code_tools.code_builder import CodeBuilder
from ...code_tools.context_namespace import ContextNamespace
from ...common import Loader
from ...compat import CompatExceptionGroup
from ...load_error import (
    AggregateLoadError,
    ExcludedTypeLoadError,
    ExtraFieldsError,
    ExtraItemsError,
    LoadError,
    NoRequiredFieldsError,
    NoRequiredItemsError,
    TypeLoadError,
)
from ...model_tools.definitions import InputField, InputShape
from ...struct_trail import append_trail, extend_trail, render_trail_as_note
from ..definitions import DebugTrail
from .crown_definitions import (
    BranchInpCrown,
    CrownPath,
    CrownPathElem,
    ExtraCollect,
    ExtraForbid,
    ExtraTargets,
    InpCrown,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameLayout,
)
from .definitions import CodeGenerator, VarBinder
from .special_cases_optimization import as_is_stub


class Namer:
    KNOWN_KEYS = 'known_keys'
    HAS_NOT_FOUND_ERROR = 'has_not_found_error'

    def __init__(
        self,
        debug_trail: DebugTrail,
        binder: VarBinder,
        path_to_suffix: Mapping[CrownPath, str],
        path: CrownPath,
    ):
        self.debug_trail = debug_trail
        self.binder = binder
        self.path_to_suffix = path_to_suffix
        self._path = path

    def _with_path_suffix(self, basis: str, path: CrownPath) -> str:
        if not path:
            return basis
        return basis + '_' + self.path_to_suffix[path]

    @property
    def path(self) -> CrownPath:
        return self._path

    @property
    def v_data(self) -> str:
        return self._with_path_suffix(self.binder.data, self._path)

    @property
    def v_known_keys(self) -> str:
        return self._with_path_suffix(self.KNOWN_KEYS, self._path)

    @property
    def v_extra(self) -> str:
        return self._with_path_suffix(self.binder.extra, self._path)

    @property
    def v_has_not_found_error(self) -> str:
        return self._with_path_suffix(self.HAS_NOT_FOUND_ERROR, self._path)

    def with_trail(self, error_expr: str) -> str:
        if self.debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
            if len(self._path) == 0:
                return error_expr
            if len(self._path) == 1:
                return f"append_trail({error_expr}, {self._path[0]!r})"
            return f"extend_trail({error_expr}, {self._path!r})"
        return error_expr

    def emit_error(self, error_expr: str) -> str:
        if self.debug_trail == DebugTrail.ALL:
            return f"errors.append({self.with_trail(error_expr)})"
        return f"raise {self.with_trail(error_expr)}"


class GenState(Namer):
    path_to_suffix: Dict[CrownPath, str]

    def __init__(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        name_to_field: Dict[str, InputField],
        debug_trail: DebugTrail,
        root_crown: InpCrown,
    ):
        self.builder = builder
        self.ctx_namespace = ctx_namespace
        self._name_to_field = name_to_field

        self.field_id_to_path: Dict[str, CrownPath] = {}

        self._last_path_idx = 0
        self._parent_path: Optional[CrownPath] = None
        self._crown_stack: List[InpCrown] = [root_crown]

        self.checked_type_paths: Set[CrownPath] = set()
        super().__init__(debug_trail=debug_trail, binder=binder, path_to_suffix={}, path=())

    @property
    def parent(self) -> Namer:
        return Namer(self.debug_trail, self.binder, self.path_to_suffix, self.parent_path)

    def v_field_loader(self, field_id: str) -> str:
        return f"loader_{field_id}"

    def v_raw_field(self, field: InputField) -> str:
        return f"r_{field.id}"

    @property
    def parent_path(self) -> CrownPath:
        if self._parent_path is None:
            raise ValueError
        return self._parent_path

    @property
    def parent_crown(self) -> BranchInpCrown:
        return self._crown_stack[-2]  # type: ignore[return-value]

    @contextlib.contextmanager
    def add_key(self, crown: InpCrown, key: CrownPathElem):
        past = self._path
        past_parent = self._parent_path

        self._parent_path = self._path
        self._path += (key,)
        self._crown_stack.append(crown)
        self._last_path_idx += 1
        self.path_to_suffix[self._path] = str(self._last_path_idx)
        yield
        self._crown_stack.pop(-1)
        self._path = past
        self._parent_path = past_parent

    def get_field(self, crown: InpFieldCrown) -> InputField:
        self.field_id_to_path[crown.id] = self._path
        return self._name_to_field[crown.id]


class BuiltinInputExtractionGen(CodeGenerator):
    """BuiltinInputExtractionGen generates code that extracts raw values from input data,
    calls loaders and stores results to variables.
    """

    def __init__(
        self,
        shape: InputShape,
        name_layout: InputNameLayout,
        debug_trail: DebugTrail,
        strict_coercion: bool,
        field_loaders: Mapping[str, Loader],
    ):
        self._shape = shape
        self._name_layout = name_layout
        self._debug_trail = debug_trail
        self._strict_coercion = strict_coercion
        self._name_to_field: Dict[str, InputField] = {
            field.id: field for field in self._shape.fields
        }
        self._field_loaders = field_loaders

    @property
    def _can_collect_extra(self) -> bool:
        return self._name_layout.extra_move is not None

    def _is_extra_target(self, field: InputField) -> bool:
        return (
            isinstance(self._name_layout.extra_move, ExtraTargets)
            and
            field.id in self._name_layout.extra_move.fields
        )

    def _create_state(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> GenState:
        return GenState(
            builder=CodeBuilder(),
            binder=binder,
            ctx_namespace=ctx_namespace,
            name_to_field=self._name_to_field,
            debug_trail=self._debug_trail,
            root_crown=self._name_layout.crown,
        )

    def __call__(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        state = self._create_state(binder, ctx_namespace)

        for field_id, loader in self._field_loaders.items():
            state.ctx_namespace.add(state.v_field_loader(field_id), loader)

        for named_value in (
            append_trail, extend_trail, render_trail_as_note,
            ExtraFieldsError, ExtraItemsError,
            NoRequiredFieldsError, NoRequiredItemsError,
            TypeLoadError, ExcludedTypeLoadError,
            LoadError, AggregateLoadError,
        ):
            state.ctx_namespace.add(named_value.__name__, named_value)  # type: ignore[attr-defined]

        state.ctx_namespace.add('CompatExceptionGroup', CompatExceptionGroup)
        state.ctx_namespace.add('CollectionsMapping', collections.abc.Mapping)
        state.ctx_namespace.add('CollectionsSequence', collections.abc.Sequence)

        if self._debug_trail == DebugTrail.ALL:
            state.builder += "errors = []"
            state.builder += "has_unexpected_error = False"
            state.ctx_namespace.add('constructor', self._shape.constructor)

        has_optional_fields = any(
            fld.is_optional and not self._is_extra_target(fld)
            for fld in self._shape.fields
        )
        if has_optional_fields:
            state.builder += f"{binder.opt_fields} = {{}}"

        if not self._gen_root_crown_dispatch(state, self._name_layout.crown):
            raise TypeError

        self._gen_extra_targets_assigment(state)

        if self._debug_trail == DebugTrail.ALL:
            state.builder(
                """
                if errors:
                    if has_unexpected_error:
                        raise CompatExceptionGroup(
                            f'while loading model {constructor}',
                            [render_trail_as_note(e) for e in errors],
                        )
                    raise AggregateLoadError(
                        f'while loading model {constructor}',
                        [render_trail_as_note(e) for e in errors],
                    )
                """
            )
            state.builder.empty_line()

        self._gen_header(state)
        return state.builder

    def _gen_header(self, state: GenState):
        header_builder = CodeBuilder()
        if state.path_to_suffix:
            header_builder += "# suffix to path"
            for path, suffix in state.path_to_suffix.items():
                header_builder += f"# {suffix} -> {list(path)}"

            header_builder.empty_line()

        if state.field_id_to_path:
            header_builder += "# field to path"
            for f_name, path in state.field_id_to_path.items():
                header_builder += f"# {f_name} -> {list(path)}"

            header_builder.empty_line()

        state.builder.extend_above(header_builder)

    def _gen_root_crown_dispatch(self, state: GenState, crown: InpCrown) -> bool:
        """Returns True if code is generated"""
        if isinstance(crown, InpDictCrown):
            self._gen_dict_crown(state, crown)
        elif isinstance(crown, InpListCrown):
            self._gen_list_crown(state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, state: GenState, sub_crown: InpCrown, key: CrownPathElem):
        with state.add_key(sub_crown, key):
            if self._gen_root_crown_dispatch(state, sub_crown):
                return
            if isinstance(sub_crown, InpFieldCrown):
                self._gen_field_crown(state, sub_crown)
                return
            if isinstance(sub_crown, InpNoneCrown):
                self._gen_none_crown(state, sub_crown)
                return

            raise TypeError

    def _gen_raise_bad_type_error(
        self,
        state: GenState,
        bad_type_load_error: str,
        namer: Optional[Namer] = None,
    ) -> None:
        if namer is None:
            namer = state

        if not namer.path and self._debug_trail == DebugTrail.ALL:
            state.builder(
                f"""
                raise AggregateLoadError(
                    f'while loading model {{constructor}}',
                    [render_trail_as_note({namer.with_trail(bad_type_load_error)})],
                )
                """
            )
        else:
            state.builder(
                f'raise {namer.with_trail(bad_type_load_error)}'
            )

    def _gen_assigment_from_parent_data(self, state: GenState, *, assign_to: str, ignore_lookup_error=False):
        last_path_el = state.path[-1]
        if isinstance(last_path_el, str):
            lookup_error = 'KeyError'
            bad_type_error = '(TypeError, IndexError)'
            bad_type_load_error = 'TypeLoadError(CollectionsMapping)'
            not_found_error = f"NoRequiredFieldsError({state.parent.v_known_keys} - set({state.parent.v_data}))"
        else:
            lookup_error = 'IndexError'
            bad_type_error = '(TypeError, KeyError)'
            bad_type_load_error = 'TypeLoadError(CollectionsSequence)'
            not_found_error = f"NoRequiredItemsError({len(state.parent_crown.map)})"

        with state.builder(
            f"""
                try:
                    {assign_to} = {state.parent.v_data}[{last_path_el!r}]
                except {lookup_error}:
            """,
        ):
            if ignore_lookup_error:
                state.builder += 'pass'
            elif self._debug_trail == DebugTrail.ALL:
                if isinstance(state.path[-1], str):
                    state.builder += f"""
                        if not {state.parent.v_has_not_found_error}:
                            errors.append({state.parent.with_trail(not_found_error)})
                            {state.parent.v_has_not_found_error} = True
                    """
                else:
                    state.builder += 'pass'
            else:
                state.builder += f"raise {state.parent.with_trail(not_found_error)}"

        if state.parent_path not in state.checked_type_paths:
            with state.builder(f'except {bad_type_error}:'):
                self._gen_raise_bad_type_error(state, bad_type_load_error, namer=state.parent)
            state.checked_type_paths.add(state.parent_path)

        if self._debug_trail == DebugTrail.FIRST:
            state.builder(
                f"""
                except Exception as e:
                    {state.with_trail('e')}
                    raise
                """
            )
        elif self._debug_trail == DebugTrail.ALL:
            state.builder(
                f"""
                except Exception as e:
                    errors.append({state.with_trail('e')})
                    has_unexpected_error = True
                """
            )

    def _gen_add_self_extra_to_parent_extra(self, state: GenState):
        if not state.path:
            return

        state.builder(f"{state.parent.v_extra}[{state.path[-1]!r}] = {state.v_extra}")
        state.builder.empty_line()

    @contextlib.contextmanager
    def _maybe_wrap_with_type_load_error_catching(self, state: GenState):
        if self._debug_trail != DebugTrail.ALL or not state.path:
            yield
            return

        with state.builder('try:'):
            yield
        state.builder(
            """
            except TypeLoadError as e:
                errors.append(e)
            """
        )
        state.builder.empty_line()

    def _gen_dict_crown(self, state: GenState, crown: InpDictCrown):
        state.ctx_namespace.add(state.v_known_keys, set(crown.map.keys()))

        if state.path:
            self._gen_assigment_from_parent_data(state, assign_to=state.v_data)
            state.builder.empty_line()

        if self._can_collect_extra:
            state.builder += f"{state.v_extra} = {{}}"
        if self._debug_trail == DebugTrail.ALL:
            state.builder += f"{state.v_has_not_found_error} = False"

        with self._maybe_wrap_with_type_load_error_catching(state):
            if crown.map:
                for key, value in crown.map.items():
                    self._gen_crown_dispatch(state, value, key)
            else:
                with state.builder(f'if not isinstance({state.v_data}, CollectionsMapping):'):
                    self._gen_raise_bad_type_error(state, 'TypeLoadError(CollectionsMapping)')
                state.builder.empty_line()

            data = state.v_data
            extra = state.v_extra
            if crown.extra_policy == ExtraForbid():
                state.builder += f"""
                    {extra}_set = set({data}) - {state.v_known_keys}
                    if {extra}_set:
                        {state.emit_error(f"ExtraFieldsError({extra}_set)")}
                """
                state.builder.empty_line()
            elif crown.extra_policy == ExtraCollect():
                state.builder += f"""
                    for key in set({data}) - {state.v_known_keys}:
                        {extra}[key] = {data}[key]
                """
                state.builder.empty_line()

        if self._can_collect_extra:
            self._gen_add_self_extra_to_parent_extra(state)

    def _gen_forbidden_sequence_check(self, state: GenState) -> None:
        with state.builder(f'if type({state.v_data}) is str:'):
            self._gen_raise_bad_type_error(state, 'ExcludedTypeLoadError(CollectionsSequence, str)')

    def _gen_list_crown(self, state: GenState, crown: InpListCrown):
        if state.path:
            self._gen_assigment_from_parent_data(state, assign_to=state.v_data)
            state.builder.empty_line()

        if self._can_collect_extra:
            list_literal: list = [
                {} if isinstance(sub_crown, (InpFieldCrown, InpNoneCrown)) else None
                for sub_crown in crown.map
            ]
            state.builder(f"{state.v_extra} = {list_literal!r}")

        with self._maybe_wrap_with_type_load_error_catching(state):
            if self._strict_coercion:
                self._gen_forbidden_sequence_check(state)

            if crown.map:
                for key, value in enumerate(crown.map):
                    self._gen_crown_dispatch(state, value, key)
            else:
                with state.builder(f'if not isinstance({state.v_data}, CollectionsSequence):'):
                    self._gen_raise_bad_type_error(state, 'TypeLoadError(CollectionsSequence)')
                state.builder.empty_line()

            list_len = len(crown.map)

            if crown.extra_policy == ExtraForbid():
                state.builder += f"""
                    if len({state.v_data}) != {list_len}:
                        if len({state.v_data}) < {list_len}:
                            {state.emit_error(f"NoRequiredItemsError({list_len})")}
                        else:
                            {state.emit_error(f"ExtraItemsError({list_len})")}
                """
            else:
                state.builder += f"""
                    if len({state.v_data}) < {list_len}:
                        {state.emit_error(f"NoRequiredItemsError({list_len})")}
                """

        if self._can_collect_extra:
            self._gen_add_self_extra_to_parent_extra(state)

    def _gen_field_crown(self, state: GenState, crown: InpFieldCrown):
        field = state.get_field(crown)
        if field.is_required:
            field_assign_to = state.binder.field(field)
            ignore_lookup_error = False
        else:
            field_assign_to = f"{state.binder.opt_fields}[{field.id!r}]"
            ignore_lookup_error = True

        self._gen_assigment_from_parent_data(
            state=state,
            assign_to=state.v_raw_field(field),
            ignore_lookup_error=ignore_lookup_error,
        )
        with state.builder('else:'):
            self._gen_field_assigment(
                assign_to=field_assign_to,
                field_id=field.id,
                loader_arg=state.v_raw_field(field),
                state=state,
            )
        state.builder.empty_line()

    def _gen_field_assigment(
        self,
        assign_to: str,
        field_id: str,
        loader_arg: str,
        state: GenState,
    ):
        if self._field_loaders[field_id] == as_is_stub:
            processing_expr = loader_arg
        else:
            field_loader = state.v_field_loader(field_id)
            processing_expr = f'{field_loader}({loader_arg})'

        if self._debug_trail in (DebugTrail.ALL, DebugTrail.FIRST):
            state.builder(
                f"""
                try:
                    {assign_to} = {processing_expr}
                except Exception as e:
                    {state.emit_error('e')}
                """
            )
        else:
            state.builder(
                f"{assign_to} = {processing_expr}"
            )

    def _gen_extra_targets_assigment(self, state: GenState):
        # Saturate extra targets with data.
        # If extra data is not collected, loader of the required field will get empty dict
        extra_move = self._name_layout.extra_move

        if not isinstance(extra_move, ExtraTargets):
            return

        if self._name_layout.crown.extra_policy == ExtraCollect():
            for target in extra_move.fields:
                field = self._name_to_field[target]

                self._gen_field_assigment(
                    assign_to=state.binder.field(field),
                    field_id=target,
                    loader_arg=state.v_extra,
                    state=state,
                )
        else:
            for target in extra_move.fields:
                field = self._name_to_field[target]
                if field.is_required:
                    self._gen_field_assigment(
                        assign_to=state.binder.field(field),
                        field_id=target,
                        loader_arg="{}",
                        state=state,
                    )

        state.builder.empty_line()

    def _gen_none_crown(self, state: GenState, crown: InpNoneCrown):
        pass
