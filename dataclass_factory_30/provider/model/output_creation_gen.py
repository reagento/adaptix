import contextlib
from typing import Dict, NamedTuple, Optional

from ...code_tools import CodeBuilder, ContextNamespace, get_literal_expr
from ...model_tools import DefaultFactory, DefaultValue, OutputField
from .crown_definitions import (
    CrownPathElem,
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    RootOutCrown,
    Sieve
)
from .definitions import CodeGenerator, OutputFigure, VarBinder
from .input_extraction_gen import CrownPath


class GenState:
    def __init__(self, binder: VarBinder, ctx_namespace: ContextNamespace, name_to_field: Dict[str, OutputField]):
        self.binder = binder
        self.ctx_namespace = ctx_namespace
        self._name_to_field = name_to_field

        self.field_name2path: Dict[str, CrownPath] = {}
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

    def crown_var(self, key: CrownPathElem) -> str:
        return self._crown_var_for_path(self._path + (key,))

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


class LinkExpr(NamedTuple):
    expr: str
    is_atomic: bool


class BuiltinOutputCreationGen(CodeGenerator):
    def __init__(self, figure: OutputFigure, crown: RootOutCrown, debug_path: bool):
        self._figure = figure
        self._root_crown = crown
        self._debug_path = debug_path

        self._name_to_field = {field.name: field for field in self._figure.fields}

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

    def _create_state(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> GenState:
        return GenState(binder, ctx_namespace, self._name_to_field)

    def __call__(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        crown_builder = CodeBuilder()
        state = self._create_state(binder, ctx_namespace)

        if not self._gen_root_crown_dispatch(crown_builder, state, self._root_crown):
            raise TypeError

        crown_builder += f"return {state.crown_var_self()}"

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

    def _gen_crown_link_expr(self, state: GenState, key: CrownPathElem, crown: OutCrown) -> LinkExpr:
        if isinstance(crown, OutNoneCrown):
            if isinstance(crown.filler, DefaultFactory):
                state.ctx_namespace.add(state.filler(), crown.filler)
                return LinkExpr(state.filler() + '()', is_atomic=False)
            if isinstance(crown.filler, DefaultValue):
                literal_expr = get_literal_expr(crown.filler)
                if literal_expr is not None:
                    return LinkExpr(literal_expr, is_atomic=True)

                state.ctx_namespace.add(state.filler(), crown.filler)
                return LinkExpr(state.filler(), is_atomic=True)

            raise TypeError

        if isinstance(crown, OutFieldCrown):
            return LinkExpr(state.binder.field(self._name_to_field[crown.name]), is_atomic=True)

        if isinstance(crown, (OutDictCrown, OutListCrown)):
            return LinkExpr(state.crown_var(key), is_atomic=True)

        raise TypeError

    def _is_required_crown(self, crown: OutCrown) -> bool:
        if not isinstance(crown, OutFieldCrown):
            return True

        return self._name_to_field[crown.name].is_required

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: OutDictCrown):
        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

        required_keys = [
            key for key, sub_crown in crown.map.items()
            if key not in crown.sieves and self._is_required_crown(crown)
        ]

        self_var = state.crown_var_self()

        with builder(f"{self_var} = {{"):
            for key in required_keys:
                builder += f"{key!r}: {self._gen_crown_link_expr(state, key, crown.map[key]).expr},"

        builder += "}"

        for key, sub_crown in crown.map.items():
            if key in required_keys:
                continue

            if key in crown.sieves:
                sieve = crown.sieves[key]

                self._gen_opt_dict_sub_crown_append(
                    builder, state, sieve, key, sub_crown
                )

        builder.empty_line()

    def _gen_opt_dict_sub_crown_append(
        self,
        builder: CodeBuilder,
        state: GenState,
        sieve_obj: Sieve,
        key: str,
        sub_crown: OutCrown,
    ):
        self_var = state.crown_var_self()

        sieve = state.sieve(key)
        state.ctx_namespace.add(sieve, sieve_obj)

        if isinstance(sub_crown, OutFieldCrown):
            field = self._name_to_field[sub_crown.name]

            if field.is_optional:
                builder += f"""
                    try:
                        value = {state.binder.opt_fields}[{field.name!r}]
                    except KeyError:
                        pass
                    else:
                        if {sieve}(value):
                            {self_var}[{key!r}] = value
                """
                builder.empty_line()
                return

        link_expr = self._gen_crown_link_expr(state, key, sub_crown)
        if link_expr.is_atomic:
            builder += f"""
                if {sieve}({link_expr.expr}):
                    {self_var}[{key!r}] = {link_expr.expr}
            """
        else:
            builder += f"""
                value = {link_expr.expr}
                if {sieve}(value):
                    {self_var}[{key!r}] = value
            """

        builder.empty_line()

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: OutListCrown):
        for i, sub_crown in enumerate(crown.map):
            self._gen_crown_dispatch(builder, state, sub_crown, i)

        with builder(f"{state.crown_var_self()} = ["):
            for i, sub_crown in enumerate(crown.map):
                builder += self._gen_crown_link_expr(state, i, sub_crown).expr + ","

        builder += "]"

    def _gen_field_crown(self, builder: CodeBuilder, state: GenState, crown: OutFieldCrown):
        state.field_name2path[crown.name] = state.path

    def _gen_none_crown(self, builder: CodeBuilder, state: GenState, crown: OutNoneCrown):
        pass
