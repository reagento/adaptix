import contextlib
from string import Template
from typing import Dict, NamedTuple, Optional

from ...code_tools.code_builder import CodeBuilder
from ...code_tools.context_namespace import ContextNamespace
from ...code_tools.utils import get_literal_expr, get_literal_from_factory, is_singleton
from ...model_tools.definitions import DefaultFactory, DefaultFactoryWithSelf, DefaultValue, OutputField
from ..definitions import DebugTrail
from .crown_definitions import (
    CrownPath,
    CrownPathElem,
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameLayout,
    Sieve,
)
from .definitions import CodeGenerator, OutputShape, VarBinder
from .special_cases_optimization import get_default_clause


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


class BuiltinOutputCreationGen(CodeGenerator):
    def __init__(self, shape: OutputShape, name_layout: OutputNameLayout, debug_trail: DebugTrail):
        self._shape = shape
        self._name_layout = name_layout
        self._debug_trail = debug_trail

        self._name_to_field: Dict[str, OutputField] = {field.id: field for field in self._shape.fields}

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

    def produce_code(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
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

        builder = CodeBuilder()

        self._gen_header(builder, state)

        builder.extend(crown_builder)

        return builder

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
