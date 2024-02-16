import contextlib
from string import Template
from typing import Dict, Mapping, NamedTuple, Tuple

from ...code_tools.cascade_namespace import BuiltinCascadeNamespace, CascadeNamespace
from ...code_tools.code_builder import CodeBuilder
from ...code_tools.utils import get_literal_expr, get_literal_from_factory, is_singleton
from ...common import Dumper
from ...compat import CompatExceptionGroup
from ...definitions import DebugTrail
from ...model_tools.definitions import (
    DefaultFactory,
    DefaultFactoryWithSelf,
    DefaultValue,
    DescriptorAccessor,
    ItemAccessor,
    OutputField,
    OutputShape,
)
from ...special_cases_optimization import as_is_stub, get_default_clause
from ...struct_trail import append_trail, extend_trail, render_trail_as_note
from .basic_gen import ModelDumperGen, get_skipped_fields
from .crown_definitions import (
    CrownPath,
    CrownPathElem,
    ExtraExtract,
    ExtraTargets,
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameLayout,
    Sieve,
)


class GenState:
    def __init__(self, builder: CodeBuilder, namespace: CascadeNamespace):
        self.builder = builder
        self.namespace = namespace

        self.field_id_to_path: Dict[str, CrownPath] = {}
        self.path_to_suffix: Dict[CrownPath, str] = {}

        self._last_path_idx = 0
        self._path: CrownPath = ()

    def _ensure_path_idx(self, path: CrownPath) -> str:
        try:
            return self.path_to_suffix[path]
        except KeyError:
            self._last_path_idx += 1
            suffix = str(self._last_path_idx)
            self.path_to_suffix[path] = suffix
            return suffix

    @property
    def path(self):
        return self._path

    @contextlib.contextmanager
    def add_key(self, key: CrownPathElem):
        past = self._path

        self._path += (key,)
        self._ensure_path_idx(self._path)
        yield
        self._path = past

    def _with_path_suffix(self, basis: str, extra_path: CrownPath = ()) -> str:
        if not self._path and not extra_path:
            return basis
        return basis + '_' + self._ensure_path_idx(self._path + extra_path)

    @property
    def v_crown(self) -> str:
        return self._with_path_suffix('result')

    @property
    def v_placeholder(self) -> str:
        return self._with_path_suffix('placeholder')

    def v_sieve(self, key: CrownPathElem) -> str:
        return self._with_path_suffix('sieve', (key,))

    def v_default(self, key: CrownPathElem) -> str:
        return self._with_path_suffix('dfl', (key,))


class ElementExpr(NamedTuple):
    expr: str
    can_inline: bool


class BuiltinModelDumperGen(ModelDumperGen):
    def __init__(
        self,
        shape: OutputShape,
        name_layout: OutputNameLayout,
        debug_trail: DebugTrail,
        fields_dumpers: Mapping[str, Dumper],
        model_identity: str,
    ):
        self._shape = shape
        self._name_layout = name_layout
        self._debug_trail = debug_trail
        self._fields_dumpers = fields_dumpers
        self._extra_targets = (
            self._name_layout.extra_move.fields
            if isinstance(self._name_layout.extra_move, ExtraTargets)
            else ()
        )
        self._id_to_field: Dict[str, OutputField] = {field.id: field for field in self._shape.fields}
        self._model_identity = model_identity

    def produce_code(self, closure_name: str) -> Tuple[str, Mapping[str, object]]:
        body_builder = CodeBuilder()

        namespace = BuiltinCascadeNamespace()
        namespace.add_constant('CompatExceptionGroup', CompatExceptionGroup)
        namespace.add_constant("append_trail", append_trail)
        namespace.add_constant("extend_trail", extend_trail)
        for field_id, dumper in self._fields_dumpers.items():
            namespace.add_constant(self._v_dumper(self._id_to_field[field_id]), dumper)

        if self._debug_trail == DebugTrail.ALL:
            body_builder('errors = []')
            body_builder.empty_line()

        if any(field.is_optional for field in self._shape.fields):
            body_builder("opt_fields = {}")
            body_builder.empty_line()

        skipped_fields = get_skipped_fields(self._shape, self._name_layout)
        for field in self._shape.fields:
            if field.id in skipped_fields:
                continue
            if not self._is_extra_target(field):
                self._gen_field_extraction(
                    body_builder, namespace, field,
                    on_access_error="pass",
                    on_access_ok_req=f"{self._v_field(field)} = $expr",
                    on_access_ok_opt=f"opt_fields[{field.id!r}] = $expr",
                )

        self._gen_extra_extraction(body_builder, namespace)

        state = self._create_state(body_builder, namespace)

        if not self._gen_root_crown_dispatch(state, self._name_layout.crown):
            raise TypeError

        if self._name_layout.extra_move is None:
            state.builder += f"return {state.v_crown}"
        else:
            state.builder += Template("return {**$var_self, **extra}").substitute(
                var_self=state.v_crown,
            )

        self._gen_header(state)

        builder = CodeBuilder()
        with builder(f'def {closure_name}(data):'):
            builder.extend(body_builder)
        return builder.string(), namespace.constants

    def _is_extra_target(self, field: OutputField) -> bool:
        return field.id in self._extra_targets

    def _v_field(self, field: OutputField) -> str:
        return f'f_{field.id}'

    def _v_dumper(self, field: OutputField) -> str:
        return f"dumper_{field.id}"

    def _v_raw_field(self, field: OutputField) -> str:
        return f"r_{field.id}"

    def _v_accessor_getter(self, field: OutputField) -> str:
        return f"accessor_getter_{field.id}"

    def _v_trail_element(self, field: OutputField) -> str:
        return f"trail_element_{field.id}"

    def _v_access_error(self, field: OutputField) -> str:
        return f"access_error_{field.id}"

    def _gen_access_expr(self, namespace: CascadeNamespace, field: OutputField) -> str:
        accessor = field.accessor
        if isinstance(accessor, DescriptorAccessor):
            if accessor.attr_name.isidentifier():
                return f"data.{accessor.attr_name}"
            return f"getattr(data, {accessor.attr_name!r})"
        if isinstance(accessor, ItemAccessor):
            return f"data[{accessor.key!r}]"

        accessor_getter = self._v_accessor_getter(field)
        namespace.add_constant(accessor_getter, field.accessor.getter)
        return f"{accessor_getter}(data)"

    def _get_trail_element_expr(self, namespace: CascadeNamespace, field: OutputField) -> str:
        trail_element = field.accessor.trail_element
        literal_expr = get_literal_expr(trail_element)
        if literal_expr is not None:
            return literal_expr

        v_trail_element = self._v_trail_element(field)
        namespace.add_constant(v_trail_element, trail_element)
        return v_trail_element

    def _gen_required_field_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
        field: OutputField,
        *,
        on_access_ok: str,
    ):
        raw_access_expr = self._gen_access_expr(namespace, field)
        v_element_expr = self._get_trail_element_expr(namespace, field)

        if self._fields_dumpers[field.id] == as_is_stub:
            on_access_ok_stmt = Template(on_access_ok).substitute(expr=raw_access_expr)
        else:
            dumper = self._v_dumper(field)
            on_access_ok_stmt = Template(on_access_ok).substitute(expr=f"{dumper}({raw_access_expr})")

        if self._debug_trail == DebugTrail.ALL:
            builder += f"""
                try:
                    {on_access_ok_stmt}
                except Exception as e:
                    errors.append(append_trail(e, {v_element_expr}))
            """
        elif self._debug_trail == DebugTrail.FIRST:
            builder += f"""
                try:
                    {on_access_ok_stmt}
                except Exception as e:
                    append_trail(e, {v_element_expr})
                    raise
            """
        else:
            builder += on_access_ok_stmt

        builder.empty_line()

    def _gen_optional_field_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
        field: OutputField,
        *,
        on_access_error: str,
        on_access_ok: str,
    ):
        raw_access_expr = self._gen_access_expr(namespace, field)
        path_element_expr = self._get_trail_element_expr(namespace, field)

        v_raw_field = self._v_raw_field(field)
        if self._fields_dumpers[field.id] == as_is_stub:
            on_access_ok_stmt = Template(on_access_ok).substitute(
                expr=v_raw_field,
            )
        else:
            dumper = self._v_dumper(field)
            on_access_ok_stmt = Template(on_access_ok).substitute(
                expr=f"{dumper}({v_raw_field})",
            )

        access_error = field.accessor.access_error
        access_error_expr = get_literal_expr(access_error)
        if access_error_expr is None:
            access_error_expr = self._v_access_error(field)
            namespace.add_constant(access_error_expr, access_error)

        if self._debug_trail == DebugTrail.ALL:
            builder += f"""
                try:
                    {v_raw_field} = {raw_access_expr}
                except {access_error_expr}:
                    {on_access_error}
                else:
                    try:
                        {on_access_ok_stmt}
                    except Exception as e:
                        errors.append(append_trail(e, {path_element_expr}))
            """
        elif self._debug_trail == DebugTrail.FIRST:
            builder += f"""
                try:
                    {v_raw_field} = {raw_access_expr}
                except {access_error_expr}:
                    {on_access_error}
                else:
                    try:
                        {on_access_ok_stmt}
                    except Exception as e:
                        append_trail(e, {path_element_expr})
                        raise
            """
        else:
            builder += f"""
                try:
                    {v_raw_field} = {raw_access_expr}
                except {access_error_expr}:
                    {on_access_error}
                else:
                    {on_access_ok_stmt}
            """

        builder.empty_line()

    def _gen_field_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
        field: OutputField,
        *,
        on_access_ok_req: str,
        on_access_ok_opt: str,
        on_access_error: str,
    ):
        if field.is_required:
            self._gen_required_field_extraction(
                builder, namespace, field,
                on_access_ok=on_access_ok_req,
            )
        else:
            self._gen_optional_field_extraction(
                builder, namespace, field,
                on_access_ok=on_access_ok_opt,
                on_access_error=on_access_error,
            )

    def _gen_raising_extraction_errors(self, builder: CodeBuilder, namespace):
        if self._debug_trail != DebugTrail.ALL:
            return

        namespace.add_constant('model_identity', self._model_identity)
        namespace.add_constant('render_trail_as_note', render_trail_as_note)
        builder(
            """
            if errors:
                raise CompatExceptionGroup(
                    f'while dumping model {model_identity}',
                    [render_trail_as_note(e) for e in errors],
                )
            """
        )

    def _gen_extra_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
    ):
        if isinstance(self._name_layout.extra_move, ExtraTargets):
            self._gen_extra_target_extraction(builder, namespace)
        elif isinstance(self._name_layout.extra_move, ExtraExtract):
            self._gen_extra_extract_extraction(builder, namespace, self._name_layout.extra_move)
        elif self._name_layout.extra_move is None:
            self._gen_raising_extraction_errors(builder, namespace)
        else:
            raise ValueError

    def _gen_extra_target_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
    ):
        if len(self._extra_targets) == 1:
            field = self._id_to_field[self._extra_targets[0]]

            self._gen_field_extraction(
                builder, namespace, field,
                on_access_error="extra = {}",
                on_access_ok_req="extra = $expr",
                on_access_ok_opt="extra = $expr",
            )
            self._gen_raising_extraction_errors(builder, namespace)

        elif all(field.is_required for field in self._id_to_field.values()):
            for field_id in self._extra_targets:
                field = self._id_to_field[field_id]

                self._gen_required_field_extraction(
                    builder, namespace, field,
                    on_access_ok=f"{self._v_field(field)} = $expr",
                )

            self._gen_raising_extraction_errors(builder, namespace)
            builder += 'extra = {'
            builder <<= ", ".join(
                "**" + self._v_field(self._id_to_field[field_id])
                for field_id in self._extra_targets
            )
            builder <<= '}'
        else:
            builder += "extra_stack = []"
            for field_id in self._extra_targets:
                field = self._id_to_field[field_id]

                self._gen_field_extraction(
                    builder, namespace, field,
                    on_access_ok_req="extra_stack.append($expr)",
                    on_access_ok_opt="extra_stack.append($expr)",
                    on_access_error="pass",
                )

            self._gen_raising_extraction_errors(builder, namespace)
            builder += """
                extra = {
                    key: value for extra_element in extra_stack for key, value in extra_element.items()
                }
            """

    def _gen_extra_extract_extraction(
        self,
        builder: CodeBuilder,
        namespace: CascadeNamespace,
        extra_move: ExtraExtract,
    ):
        namespace.add_constant('extractor', extra_move.func)

        if self._debug_trail == DebugTrail.ALL:
            builder += """
                try:
                    extra = extractor(data)
                except Exception as e:
                    errors.append(e)
            """
        else:
            builder += "extra = extractor(data)"

        self._gen_raising_extraction_errors(builder, namespace)
        builder.empty_line()

    def _gen_header(self, state: GenState):
        builder = CodeBuilder()
        if state.path_to_suffix:
            builder += "# suffix to path"
            for path, suffix in state.path_to_suffix.items():
                builder += f"# {suffix} -> {list(path)}"

            builder.empty_line()

        if state.field_id_to_path:
            builder += "# field to path"
            for f_name, path in state.field_id_to_path.items():
                builder += f"# {f_name} -> {list(path)}"

            builder.empty_line()

        state.builder.extend_above(builder)

    def _create_state(self, builder: CodeBuilder, namespace: CascadeNamespace) -> GenState:
        return GenState(builder, namespace)

    def _gen_root_crown_dispatch(self, state: GenState, crown: OutCrown):
        if isinstance(crown, OutDictCrown):
            self._gen_dict_crown(state, crown)
        elif isinstance(crown, OutListCrown):
            self._gen_list_crown(state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, state: GenState, sub_crown: OutCrown, key: CrownPathElem):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(state, sub_crown):
                return
            if isinstance(sub_crown, OutFieldCrown):
                self._gen_field_crown(state, sub_crown)
                return
            if isinstance(sub_crown, OutNoneCrown):
                self._gen_none_crown(state, sub_crown)
                return

            raise TypeError

    def _get_element_expr_for_none_crown(self, state: GenState, crown: OutNoneCrown) -> ElementExpr:
        if isinstance(crown.placeholder, DefaultFactory):
            literal_expr = get_literal_from_factory(crown.placeholder.factory)
            if literal_expr is not None:
                return ElementExpr(literal_expr, can_inline=True)

            state.namespace.add_constant(state.v_placeholder, crown.placeholder.factory)
            return ElementExpr(state.v_placeholder + '()', can_inline=False)

        if isinstance(crown.placeholder, DefaultValue):
            literal_expr = get_literal_expr(crown.placeholder.value)
            if literal_expr is not None:
                return ElementExpr(literal_expr, can_inline=True)

            state.namespace.add_constant(state.v_placeholder, crown.placeholder.value)
            return ElementExpr(state.v_placeholder, can_inline=True)

        raise TypeError

    def _get_element_expr(self, state: GenState, key: CrownPathElem, crown: OutCrown) -> ElementExpr:
        with state.add_key(key):
            if isinstance(crown, OutNoneCrown):
                return self._get_element_expr_for_none_crown(state, crown)

            if isinstance(crown, OutFieldCrown):
                field = self._id_to_field[crown.id]
                if field.is_required:
                    field_expr = self._v_field(field)
                else:
                    raise ValueError("Can not generate ElementExpr for optional field")
                return ElementExpr(field_expr, can_inline=True)

            if isinstance(crown, (OutDictCrown, OutListCrown)):
                return ElementExpr(state.v_crown, can_inline=True)

            raise TypeError

    def _is_required_crown(self, crown: OutCrown) -> bool:
        if not isinstance(crown, OutFieldCrown):
            return True

        return self._id_to_field[crown.id].is_required

    def _gen_dict_crown(self, state: GenState, crown: OutDictCrown):
        for key, value in crown.map.items():
            self._gen_crown_dispatch(state, value, key)

        required_keys = [
            key for key, sub_crown in crown.map.items()
            if key not in crown.sieves and self._is_required_crown(sub_crown)
        ]
        if required_keys:
            with state.builder(f"{state.v_crown} = {{"):
                for key in required_keys:
                    state.builder += f"{key!r}: {self._get_element_expr(state, key, crown.map[key]).expr},"

            state.builder += "}"
        else:
            state.builder += f"{state.v_crown} = {{}}"

        for key, sub_crown in crown.map.items():
            if key in required_keys:
                continue

            self._gen_dict_optional_crown_fragment(state, crown, key, sub_crown)

        if not crown.map:
            state.builder.empty_line()

    def _gen_dict_optional_crown_fragment(
        self,
        state: GenState,
        crown: OutDictCrown,
        key: str,
        sub_crown: OutCrown
    ):
        if isinstance(sub_crown, OutFieldCrown) and self._id_to_field[sub_crown.id].is_optional:
            with state.builder(
                f"""
                try:
                    value = opt_fields[{sub_crown.id!r}]
                except KeyError:
                    pass
                else:
                """
            ):
                if key in crown.sieves:
                    self._gen_dict_sieved_append(
                        state, crown.sieves[key], key,
                        element_expr=ElementExpr('value', can_inline=True),
                    )
                else:
                    state.builder(f"{state.v_crown}[{key!r}] = value")
        else:
            element_expr = self._get_element_expr(state, key, sub_crown)
            self._gen_dict_sieved_append(
                state, crown.sieves[key], key, element_expr
            )

    def _gen_dict_sieved_append(
        self,
        state: GenState,
        sieve: Sieve,
        key: str,
        element_expr: ElementExpr,
    ):
        condition = self._get_sieve_condition(state, sieve, key, element_expr.expr)
        if element_expr.can_inline:
            state.builder += f"""
                if {condition}:
                    {state.v_crown}[{key!r}] = {element_expr.expr}
            """
        else:
            state.builder += f"""
                value = {element_expr.expr}
                if {condition}:
                    {state.v_crown}[{key!r}] = value
            """
        state.builder.empty_line()

    def _get_sieve_condition(self, state: GenState, sieve: Sieve, key: str, input_expr: str) -> str:
        default_clause = get_default_clause(sieve)
        if default_clause is None:
            v_sieve = state.v_sieve(key)
            state.namespace.add_constant(v_sieve, sieve)
            return f'{v_sieve}({input_expr})'

        if isinstance(default_clause, DefaultValue):
            literal_expr = get_literal_expr(default_clause.value)
            if literal_expr is not None:
                return (
                    f"{input_expr} is not {literal_expr}"
                    if is_singleton(default_clause.value) else
                    f"{input_expr} != {literal_expr}"
                )
            v_default = state.v_default(key)
            state.namespace.add_constant(v_default, default_clause.value)
            return f"{input_expr} != {v_default}"

        if isinstance(default_clause, DefaultFactory):
            literal_expr = get_literal_from_factory(default_clause.factory)
            if literal_expr is not None:
                return f"{input_expr} != {literal_expr}"
            v_default = state.v_default(key)
            state.namespace.add_constant(v_default, default_clause.factory)
            return f"{input_expr} != {v_default}()"

        if isinstance(default_clause, DefaultFactoryWithSelf):
            v_default = state.v_default(key)
            state.namespace.add_constant(v_default, default_clause.factory)
            return f"{input_expr} != {v_default}(data)"

        raise TypeError

    def _gen_list_crown(self, state: GenState, crown: OutListCrown):
        for i, sub_crown in enumerate(crown.map):
            self._gen_crown_dispatch(state, sub_crown, i)

        with state.builder(f"{state.v_crown} = ["):
            for i, sub_crown in enumerate(crown.map):
                state.builder += self._get_element_expr(state, i, sub_crown).expr + ","

        state.builder += "]"

    def _gen_field_crown(self, state: GenState, crown: OutFieldCrown):
        state.field_id_to_path[crown.id] = state.path

    def _gen_none_crown(self, state: GenState, crown: OutNoneCrown):
        pass
