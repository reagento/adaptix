import contextlib
from string import Template
from typing import Dict, Mapping, NamedTuple, Optional

from ...code_tools.code_builder import CodeBuilder
from ...code_tools.context_namespace import ContextNamespace
from ...code_tools.utils import get_literal_expr, get_literal_from_factory, is_singleton
from ...common import Dumper
from ...model_tools.definitions import (
    DefaultFactory,
    DefaultFactoryWithSelf,
    DefaultValue,
    DescriptorAccessor,
    ItemAccessor,
    OutputField,
    OutputShape,
)
from ...struct_trail import append_trail, extend_trail
from ..definitions import DebugTrail
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
from .definitions import CodeGenerator, VarBinder
from .special_cases_optimization import as_is_stub, get_default_clause


class GenState:
    def __init__(self, binder: VarBinder, ctx_namespace: ContextNamespace, name_to_field: Dict[str, OutputField]):
        self.binder = binder
        self.ctx_namespace = ctx_namespace
        self._name_to_field = name_to_field

        self.field_id2path: Dict[str, CrownPath] = {}
        self.path2suffix: Dict[CrownPath, str] = {}

        self._last_path_idx = 0
        self._path: CrownPath = ()
        self._parent_path: Optional[CrownPath] = None

    def _get_path_idx(self, path: CrownPath) -> str:
        try:
            return self.path2suffix[path]
        except KeyError:
            self._last_path_idx += 1
            suffix = str(self._last_path_idx)
            self.path2suffix[path] = suffix
            return suffix

    @property
    def path(self):
        return self._path

    @contextlib.contextmanager
    def add_key(self, key: CrownPathElem):
        past = self._path

        self._path += (key,)
        yield
        self._path = past

    def crown_var(self) -> str:
        return self._crown_var_for_path(self._path)

    def crown_var_self(self) -> str:
        return self._crown_var_for_path(self._path)

    def _crown_var_for_path(self, path: CrownPath) -> str:
        if not path:
            return "result"

        return 'result_' + self._get_path_idx(path)

    def filler(self) -> str:
        if not self._path:
            return "filler"

        return 'filler_' + self._get_path_idx(self._path)

    def sieve(self, key: CrownPathElem) -> str:
        path = self._path + (key,)
        if not path:
            return "sieve"

        return 'sieve_' + self._get_path_idx(path)

    def default_clause(self, key: CrownPathElem) -> str:
        path = self._path + (key,)
        if not path:
            return "dfl"

        return 'dfl_' + self._get_path_idx(path)


class ElementExpr(NamedTuple):
    expr: str
    can_inline: bool


class BuiltinModelDumperGen(CodeGenerator):
    def __init__(
        self,
        shape: OutputShape,
        name_layout: OutputNameLayout,
        debug_trail: DebugTrail,
        fields_dumpers: Mapping[str, Dumper],
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
        self._name_to_field: Dict[str, OutputField] = {field.id: field for field in self._shape.fields}

    def produce_code(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        builder = CodeBuilder()

        ctx_namespace.add("append_trail", append_trail)
        ctx_namespace.add("extend_trail", extend_trail)
        name_to_fields = {field.id: field for field in self._shape.fields}

        for field_id, dumper in self._fields_dumpers.items():
            ctx_namespace.add(self._dumper(name_to_fields[field_id]), dumper)

        if any(field.is_optional for field in self._shape.fields):
            builder(f"{binder.opt_fields} = {{}}")
            builder.empty_line()

        for field in self._shape.fields:
            if not self._is_extra_target(field):
                self._gen_field_extraction(
                    builder, binder, ctx_namespace, field,
                    on_access_error="pass",
                    on_access_ok_req=f"{binder.field(field)} = $expr",
                    on_access_ok_opt=f"{binder.opt_fields}[{field.id!r}] = $expr",
                )

        self._gen_extra_extraction(
            builder, binder, ctx_namespace, name_to_fields,
        )

        crown_builder = CodeBuilder()
        state = self._create_state(binder, ctx_namespace)

        if not self._gen_root_crown_dispatch(crown_builder, state, self._name_layout.crown):
            raise TypeError

        if self._name_layout.extra_move is None:
            crown_builder += f"return {state.crown_var_self()}"
        else:
            crown_builder += Template("return {**$var_self, **$extra}").substitute(
                var_self=state.crown_var_self(),
                extra=binder.extra,
            )

        self._gen_header(builder, state)
        builder.extend(crown_builder)
        return builder

    def _is_extra_target(self, field: OutputField) -> bool:
        return field.id in self._extra_targets

    def _dumper(self, field: OutputField) -> str:
        return f"dumper_{field.id}"

    def _raw_field(self, field: OutputField) -> str:
        return f"r_{field.id}"

    def _accessor_getter(self, field: OutputField) -> str:
        return f"accessor_getter_{field.id}"

    def _gen_access_expr(self, binder: VarBinder, ctx_namespace: ContextNamespace, field: OutputField) -> str:
        accessor = field.accessor
        if isinstance(accessor, DescriptorAccessor):
            if accessor.attr_name.isidentifier():
                return f"{binder.data}.{accessor.attr_name}"
            return f"getattr({binder.data}, {accessor.attr_name!r})"
        if isinstance(accessor, ItemAccessor):
            literal_expr = get_literal_expr(accessor.key)
            if literal_expr is not None:
                return f"{binder.data}[{literal_expr}]"

        accessor_getter = self._accessor_getter(field)
        ctx_namespace.add(accessor_getter, field.accessor.getter)
        return f"{accessor_getter}({binder.data})"

    def _get_path_element_var_name(self, field: OutputField) -> str:
        return f"path_element_{field.id}"

    def _gen_path_element_expr(self, ctx_namespace: ContextNamespace, field: OutputField) -> str:
        path_element = field.accessor.trail_element
        literal_expr = get_literal_expr(path_element)
        if literal_expr is not None:
            return literal_expr

        pe_var_name = self._get_path_element_var_name(field)
        ctx_namespace.add(pe_var_name, path_element)
        return pe_var_name

    def _gen_required_field_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field: OutputField,
        *,
        on_access_ok: str,
    ):
        raw_access_expr = self._gen_access_expr(binder, ctx_namespace, field)
        path_element_expr = self._gen_path_element_expr(ctx_namespace, field)

        if self._fields_dumpers[field.id] == as_is_stub:
            on_access_ok_stmt = Template(on_access_ok).substitute(expr=raw_access_expr)
        else:
            dumper = self._dumper(field)
            on_access_ok_stmt = Template(on_access_ok).substitute(expr=f"{dumper}({raw_access_expr})")

        if self._debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
            builder += f"""
                try:
                    {on_access_ok_stmt}
                except Exception as e:
                    append_trail(e, {path_element_expr})
                    raise e
            """
        else:
            builder += on_access_ok_stmt

        builder.empty_line()

    def _get_access_error_var_name(self, field: OutputField) -> str:
        return f"access_error_{field.id}"

    def _gen_optional_field_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field: OutputField,
        *,
        on_access_error: str,
        on_access_ok: str,
    ):
        raw_access_expr = self._gen_access_expr(binder, ctx_namespace, field)
        path_element_expr = self._gen_path_element_expr(ctx_namespace, field)

        raw_field = self._raw_field(field)

        if self._fields_dumpers[field.id] == as_is_stub:
            on_access_ok_stmt = Template(on_access_ok).substitute(
                expr=raw_field,
            )
        else:
            dumper = self._dumper(field)
            on_access_ok_stmt = Template(on_access_ok).substitute(
                expr=f"{dumper}({raw_field})",
            )

        access_error = field.accessor.access_error
        access_error_var = get_literal_expr(access_error)
        if access_error_var is None:
            access_error_var = self._get_access_error_var_name(field)
            ctx_namespace.add(access_error_var, access_error)

        if self._debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
            builder += f"""
                try:
                    {raw_field} = {raw_access_expr}
                except {access_error_var}:
                    {on_access_error}
                else:
                    try:
                        {on_access_ok_stmt}
                    except Exception as e:
                        append_trail(e, {path_element_expr})
                        raise e
            """
        else:
            builder += f"""
                try:
                    {raw_field} = {raw_access_expr}
                except {access_error_var}:
                    {on_access_error}
                else:
                    {on_access_ok_stmt}
            """

        builder.empty_line()

    def _gen_field_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        field: OutputField,
        *,
        on_access_ok_req: str,
        on_access_ok_opt: str,
        on_access_error: str,
    ):
        if field.is_required:
            self._gen_required_field_extraction(
                builder, binder, ctx_namespace, field,
                on_access_ok=on_access_ok_req,
            )
        else:
            self._gen_optional_field_extraction(
                builder, binder, ctx_namespace, field,
                on_access_ok=on_access_ok_opt,
                on_access_error=on_access_error,
            )

    def _gen_extra_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        name_to_fields: Dict[str, OutputField],
    ):
        if isinstance(self._name_layout.extra_move, ExtraTargets):
            self._gen_extra_target_extraction(builder, binder, ctx_namespace, name_to_fields)
        elif isinstance(self._name_layout.extra_move, ExtraExtract):
            self._gen_extra_extract_extraction(builder, binder, ctx_namespace, self._name_layout.extra_move)
        elif self._name_layout.extra_move is not None:
            raise ValueError

    def _get_extra_stack_name(self):
        return "extra_stack"

    def _gen_extra_target_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        name_to_fields: Dict[str, OutputField],
    ):
        if len(self._extra_targets) == 1:
            field = name_to_fields[self._extra_targets[0]]

            self._gen_field_extraction(
                builder, binder, ctx_namespace, field,
                on_access_error=f"{binder.extra} = {{}}",
                on_access_ok_req=f"{binder.extra} = $expr",
                on_access_ok_opt=f"{binder.extra} = $expr",
            )

        elif all(field.is_required for field in name_to_fields.values()):
            for field_id in self._extra_targets:
                field = name_to_fields[field_id]

                self._gen_required_field_extraction(
                    builder, binder, ctx_namespace, field,
                    on_access_ok=f"{binder.field(field)} = $expr",
                )

            builder += f'{binder.extra} = {{'
            builder <<= ", ".join(
                "**" + binder.field(name_to_fields[field_id])
                for field_id in self._extra_targets
            )
            builder <<= '}'
        else:
            extra_stack = self._get_extra_stack_name()

            builder += f"{extra_stack} = []"

            for field_id in self._extra_targets:
                field = name_to_fields[field_id]

                self._gen_field_extraction(
                    builder, binder, ctx_namespace, field,
                    on_access_ok_req=f"{extra_stack}.append($expr)",
                    on_access_ok_opt=f"{extra_stack}.append($expr)",
                    on_access_error="pass",
                )

            builder += f"""
                {binder.extra} = {{
                    key: value for extra_element in {extra_stack} for key, value in extra_element.items()
                }}
            """

    def _gen_extra_extract_extraction(
        self,
        builder: CodeBuilder,
        binder: VarBinder,
        ctx_namespace: ContextNamespace,
        extra_move: ExtraExtract,
    ):
        ctx_namespace.add('extractor', extra_move.func)

        builder += f"{binder.extra} = extractor({binder.data})"
        builder.empty_line()

    def _gen_header(self, builder: CodeBuilder, state: GenState):
        if state.path2suffix:
            builder += "# suffix to path"
            for path, suffix in state.path2suffix.items():
                builder += f"# {suffix} -> {list(path)}"

            builder.empty_line()

        if state.field_id2path:
            builder += "# field to path"
            for f_name, path in state.field_id2path.items():
                builder += f"# {f_name} -> {list(path)}"

            builder.empty_line()

    def _create_state(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> GenState:
        return GenState(binder, ctx_namespace, self._name_to_field)

    def _gen_root_crown_dispatch(self, builder: CodeBuilder, state: GenState, crown: OutCrown):
        if isinstance(crown, OutDictCrown):
            self._gen_dict_crown(builder, state, crown)
        elif isinstance(crown, OutListCrown):
            self._gen_list_crown(builder, state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, builder: CodeBuilder, state: GenState, sub_crown: OutCrown, key: CrownPathElem):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(builder, state, sub_crown):
                return
            if isinstance(sub_crown, OutFieldCrown):
                self._gen_field_crown(builder, state, sub_crown)
                return
            if isinstance(sub_crown, OutNoneCrown):
                self._gen_none_crown(builder, state, sub_crown)
                return

            raise TypeError

    def _get_element_expr_for_none_crown(self, state: GenState, key: CrownPathElem, crown: OutNoneCrown) -> ElementExpr:
        if isinstance(crown.filler, DefaultFactory):
            literal_expr = get_literal_from_factory(crown.filler.factory)
            if literal_expr is not None:
                return ElementExpr(literal_expr, can_inline=True)

            state.ctx_namespace.add(state.filler(), crown.filler.factory)
            return ElementExpr(state.filler() + '()', can_inline=False)

        if isinstance(crown.filler, DefaultValue):
            literal_expr = get_literal_expr(crown.filler.value)
            if literal_expr is not None:
                return ElementExpr(literal_expr, can_inline=True)

            state.ctx_namespace.add(state.filler(), crown.filler.value)
            return ElementExpr(state.filler(), can_inline=True)

        raise TypeError

    def _get_element_expr(self, state: GenState, key: CrownPathElem, crown: OutCrown) -> ElementExpr:
        with state.add_key(key):
            if isinstance(crown, OutNoneCrown):
                return self._get_element_expr_for_none_crown(state, key, crown)

            if isinstance(crown, OutFieldCrown):
                field = self._name_to_field[crown.id]
                if field.is_required:
                    field_expr = state.binder.field(field)
                else:
                    raise ValueError("Can not generate ElementExpr for optional field")
                return ElementExpr(field_expr, can_inline=True)

            if isinstance(crown, (OutDictCrown, OutListCrown)):
                return ElementExpr(state.crown_var(), can_inline=True)

            raise TypeError

    def _is_required_crown(self, crown: OutCrown) -> bool:
        if not isinstance(crown, OutFieldCrown):
            return True

        return self._name_to_field[crown.id].is_required

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: OutDictCrown):
        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

        required_keys = [
            key for key, sub_crown in crown.map.items()
            if key not in crown.sieves and self._is_required_crown(sub_crown)
        ]

        self_var = state.crown_var_self()

        if required_keys:
            with builder(f"{self_var} = {{"):
                for key in required_keys:
                    builder += f"{key!r}: {self._get_element_expr(state, key, crown.map[key]).expr},"

            builder += "}"
        else:
            builder += f"{self_var} = {{}}"

        for key, sub_crown in crown.map.items():
            if key in required_keys:
                continue

            self._gen_dict_optional_crown_fragment(builder, state, crown, key, sub_crown)

        if not crown.map:
            builder.empty_line()

    def _gen_dict_optional_crown_fragment(
        self,
        builder: CodeBuilder,
        state: GenState,
        crown: OutDictCrown,
        key: str,
        sub_crown: OutCrown
    ):
        if isinstance(sub_crown, OutFieldCrown) and self._name_to_field[sub_crown.id].is_optional:
            builder += f"""
                try:
                    value = {state.binder.opt_fields}[{sub_crown.id!r}]
                except KeyError:
                    pass
                else:
            """
            with builder:
                if key in crown.sieves:
                    self._gen_dict_sieved_append(
                        builder, state, crown.sieves[key], key,
                        element_expr=ElementExpr('value', can_inline=True)
                    )
                else:
                    self_var = state.crown_var_self()
                    builder(f"{self_var}[{key!r}] = value")
        else:
            element_expr = self._get_element_expr(state, key, sub_crown)
            self._gen_dict_sieved_append(
                builder, state, crown.sieves[key], key, element_expr
            )

    def _gen_dict_sieved_append(
        self,
        builder: CodeBuilder,
        state: GenState,
        sieve: Sieve,
        key: str,
        element_expr: ElementExpr,
    ):
        self_var = state.crown_var_self()
        condition = self._gen_sieve_condition(state, sieve, key, element_expr.expr)
        if element_expr.can_inline:
            builder += f"""
                if {condition}:
                    {self_var}[{key!r}] = {element_expr.expr}
            """
        else:
            builder += f"""
                value = {element_expr.expr}
                if {condition}:
                    {self_var}[{key!r}] = value
            """
        builder.empty_line()

    def _gen_sieve_condition(self, state: GenState, sieve: Sieve, key: str, input_expr: str) -> str:
        default_clause = get_default_clause(sieve)
        if default_clause is None:
            sieve_var = state.sieve(key)
            state.ctx_namespace.add(sieve_var, sieve)
            return f'{sieve_var}({input_expr})'

        if isinstance(default_clause, DefaultValue):
            literal_expr = get_literal_expr(default_clause.value)
            if literal_expr is not None:
                return (
                    f"{input_expr} is not {literal_expr}"
                    if is_singleton(default_clause.value) else
                    f"{input_expr} != {literal_expr}"
                )
            default_clause_var = state.default_clause(key)
            state.ctx_namespace.add(default_clause_var, default_clause.value)
            return f"{input_expr} != {default_clause_var}"

        if isinstance(default_clause, DefaultFactory):
            literal_expr = get_literal_from_factory(default_clause.factory)
            if literal_expr is not None:
                return f"{input_expr} != {literal_expr}"
            default_clause_var = state.default_clause(key)
            state.ctx_namespace.add(default_clause_var, default_clause.factory)
            return f"{input_expr} != {default_clause_var}()"

        if isinstance(default_clause, DefaultFactoryWithSelf):
            default_clause_var = state.default_clause(key)
            state.ctx_namespace.add(default_clause_var, default_clause.factory)
            return f"{input_expr} != {default_clause_var}({state.binder.data})"

        raise TypeError

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: OutListCrown):
        for i, sub_crown in enumerate(crown.map):
            self._gen_crown_dispatch(builder, state, sub_crown, i)

        with builder(f"{state.crown_var_self()} = ["):
            for i, sub_crown in enumerate(crown.map):
                builder += self._get_element_expr(state, i, sub_crown).expr + ","

        builder += "]"

    def _gen_field_crown(self, builder: CodeBuilder, state: GenState, crown: OutFieldCrown):
        state.field_id2path[crown.id] = state.path

    def _gen_none_crown(self, builder: CodeBuilder, state: GenState, crown: OutNoneCrown):
        pass
