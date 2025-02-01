import contextlib
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Callable, NamedTuple, Optional, Protocol, Union

from ...code_tools.cascade_namespace import BuiltinCascadeNamespace, CascadeNamespace
from ...code_tools.code_gen_tree import (
    CodeBlock,
    CodeExpr,
    DictItem,
    DictKeyValue,
    DictLiteral,
    Expression,
    LinesWriter,
    ListLiteral,
    MappingUnpack,
    RawExpr,
    RawStatement,
    Statement,
    StringLiteral,
    statements,
)
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
from ...struct_trail import append_trail, extend_trail
from ...utils import Omittable, Omitted
from ..json_schema.definitions import JSONSchema
from ..json_schema.schema_model import JSONSchemaType, JSONValue
from .basic_gen import ModelDumperGen
from .crown_definitions import (
    CrownPath,
    CrownPathElem,
    ExtraExtract,
    ExtraTargets,
    OutCrown,
    OutDictCrown,
    OutExtraMove,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameLayout,
    Sieve,
)


class GenState:
    def __init__(self, namespace: CascadeNamespace):
        self.namespace = namespace

        self.field_id_to_path: dict[str, CrownPath] = {}
        self.path_to_suffix: dict[CrownPath, str] = {}

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

    def suffix(self, basis: str, key: Optional[CrownPathElem] = None) -> str:
        path = self._path if key is None else (*self._path, key)
        if not path:
            return basis
        return basis + "_" + self._ensure_path_idx(path)

    def var_suffix(self, basis: str, key: Optional[CrownPathElem] = None) -> str:
        var = self.suffix(basis, key)
        self.namespace.register_var(var)
        return var

    @property
    def v_crown(self) -> str:
        return self.suffix("result")


class OutVarStatement(NamedTuple):
    stmt: Statement
    var: str


class OutVarStatementMaker(Protocol):
    def __call__(self, *, on_access_ok: Statement, on_access_error: Statement) -> Statement:
        ...


class OptionalOutVarStatement(NamedTuple):
    var: str
    stmt_maker: OutVarStatementMaker


RequiredStatement = Union[Expression, OutVarStatement]
OutStatement = Union[Expression, OutVarStatement, OptionalOutVarStatement]


class DictBuilder:
    def __init__(self) -> None:
        self.before_stmts: list[Statement] = []
        self.dict_items: list[DictItem] = []
        self.after_stmts: list[Statement] = []


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
        self._id_to_field: dict[str, OutputField] = {field.id: field for field in self._shape.fields}
        self._model_identity = model_identity

    def _v_dumper(self, field: OutputField) -> str:
        return f"dumper_{field.id}"

    def _create_state(self, namespace: CascadeNamespace) -> GenState:
        return GenState(namespace)

    def _get_header(self, state: GenState) -> Statement:
        writer = LinesWriter()
        if state.path_to_suffix:
            writer.write("# suffix to path")
            for path, suffix in state.path_to_suffix.items():
                writer.write(f"# {suffix} -> {list(path)}")

            writer.write("")

        if state.field_id_to_path:
            writer.write("# field to path")
            for f_name, path in state.field_id_to_path.items():
                writer.write(f"# {f_name} -> {list(path)}")

            writer.write("")

        return RawStatement(writer.make_string())

    def produce_code(self, closure_name: str) -> tuple[str, Mapping[str, object]]:
        namespace = BuiltinCascadeNamespace()
        namespace.add_constant("CompatExceptionGroup", CompatExceptionGroup)
        namespace.add_constant("append_trail", append_trail)
        namespace.add_constant("extend_trail", extend_trail)
        for field_id, dumper in self._fields_dumpers.items():
            namespace.add_constant(self._v_dumper(self._id_to_field[field_id]), dumper)

        state = self._create_state(namespace)
        body = self._get_body_statement(state)
        header = self._get_header(state)

        writer = LinesWriter()
        closure = CodeBlock(
            """
            def <closure_name>(data):
                <header>
                <body>
            """,
            closure_name=RawExpr(closure_name),
            header=header,
            body=body,
        )
        closure.write_lines(writer)
        if self._debug_trail == DebugTrail.ALL:
            error_handler = CodeBlock(
                """
                def error_handler(idx, data, exc):
                    pass
                """,
            )
            error_handler.write_lines(writer)
        return writer.make_string(), namespace.all_constants

    def _get_body_statement(self, state: GenState) -> Statement:
        crown_out_stmt = self._get_root_crown_stmt(state)
        extra_extraction_out_stmt = self._get_extra_extraction(state)
        if extra_extraction_out_stmt is None:
            if isinstance(crown_out_stmt, OutVarStatement):
                return statements(
                    crown_out_stmt.stmt,
                    CodeBlock(
                        "return <out_variable>",
                        out_variable=RawExpr(crown_out_stmt.var),
                    ),
                )
            return CodeBlock(
                "return <expr>",
                expr=crown_out_stmt,
            )

        if isinstance(crown_out_stmt, OutVarStatement):
            final_crown_out_stmt = crown_out_stmt
        elif isinstance(crown_out_stmt, Expression):
            state.namespace.register_var("result")
            final_crown_out_stmt = OutVarStatement(
                stmt=CodeBlock(
                    """
                    result = <expr>
                    """,
                ),
                var="result",
            )
        else:
            raise TypeError

        if isinstance(extra_extraction_out_stmt, Expression):
            extending_stmt: Statement = CodeBlock(
                "<out_variable>.update(<extra>)",
                out_variable=RawExpr(final_crown_out_stmt.var),
                extra=extra_extraction_out_stmt,
            )
        elif isinstance(extra_extraction_out_stmt, OutVarStatement):
            extending_stmt = CodeBlock(
                "<out_variable>.update(<extra>)",
                out_variable=RawExpr(final_crown_out_stmt.var),
                extra=RawExpr(extra_extraction_out_stmt.var),
            )
        elif isinstance(extra_extraction_out_stmt, OptionalOutVarStatement):
            extending_stmt = extra_extraction_out_stmt.stmt_maker(
                on_access_ok=CodeBlock("<out_variable>.update(<extra>)"),
                on_access_error=CodeBlock.PASS,
            )
        else:
            raise TypeError

        return statements(
            final_crown_out_stmt.stmt,
            extending_stmt,
            CodeBlock(
                """
                return <out_variable>
                """,
            ),
        )

    def _get_extra_extraction(self, state: GenState) -> Optional[OutStatement]:
        if isinstance(self._name_layout.extra_move, ExtraTargets):
            return self._get_extra_target_extraction(state, self._name_layout.extra_move)
        if isinstance(self._name_layout.extra_move, ExtraExtract):
            return self._get_extra_extract_extraction(state, self._name_layout.extra_move)
        if self._name_layout.extra_move is None:
            return None
        raise ValueError

    def _get_extra_target_extraction(self, state: GenState, extra_targets: ExtraTargets) -> OutStatement:
        if len(extra_targets.fields) == 1:
            return self._get_field_extraction(state, self._id_to_field[extra_targets.fields[0]])

        out_stmts = [
            self._get_field_extraction(state, self._id_to_field[field_id])
            for field_id in extra_targets.fields
        ]
        builder = DictBuilder()

        for out_stmt in out_stmts:
            if isinstance(out_stmt, Expression):
                builder.dict_items.append(MappingUnpack(out_stmt))
            elif isinstance(out_stmt, OutVarStatement):
                builder.before_stmts.append(out_stmt.stmt)
                builder.dict_items.append(MappingUnpack(RawExpr(out_stmt.var)))
            elif isinstance(out_stmt, OptionalOutVarStatement):
                builder.after_stmts.append(
                    out_stmt.stmt_maker(
                        on_access_ok=CodeBlock(
                            "extra.update(<var>)",
                            var=RawExpr(out_stmt.var),
                        ),
                        on_access_error=CodeBlock.PASS,
                    ),
                )

        dict_literal = DictLiteral(
            MappingUnpack(out_stmt if isinstance(out_stmt, Expression) else RawExpr(out_stmt.var))
            for out_stmt in out_stmts
        )
        if not builder.before_stmts and not builder.after_stmts:
            return dict_literal

        out_variable = "extra"
        state.namespace.register_var(out_variable)
        return OutVarStatement(
            stmt=statements(
                *builder.before_stmts,
                CodeBlock(
                    "<out_variable> = <main_dict>",
                    out_variable=RawExpr(out_variable),
                    main_dict=dict_literal,
                ),
                *builder.after_stmts,
            ),
            var=out_variable,
        )

    def _get_extra_extract_extraction(self, state: GenState, extra_move: ExtraExtract) -> OutStatement:
        state.namespace.add_constant("extractor", extra_move.func)

        if self._debug_trail != DebugTrail.ALL:
            return RawExpr("extra = extractor(data)")

        out_variable = "extra"
        state.namespace.register_var(out_variable)
        return OutVarStatement(
            stmt=statements(
                CodeBlock(
                    """
                        try:
                            extra = extractor(data)
                        except Exception as e:
                            raise error_handler(1, obj, append_trail(e, <trail_element>)) from None
                    """,
                ),
            ),
            var=out_variable,
        )

    def _get_access_expr(self, namespace: CascadeNamespace, field: OutputField) -> str:
        accessor = field.accessor
        if isinstance(accessor, DescriptorAccessor):
            if accessor.attr_name.isidentifier():
                return f"data.{accessor.attr_name}"
            return f"getattr(data, {accessor.attr_name!r})"
        if isinstance(accessor, ItemAccessor):
            return f"data[{accessor.key!r}]"

        accessor_getter = f"accessor_getter_{field.id}"
        namespace.add_constant(accessor_getter, field.accessor.getter)
        return f"{accessor_getter}(data)"

    def _get_trail_element_expr(self, namespace: CascadeNamespace, field: OutputField) -> str:
        trail_element = field.accessor.trail_element
        literal_expr = get_literal_expr(trail_element)
        if literal_expr is not None:
            return literal_expr

        v_trail_element = f"trail_element_{field.id}"
        namespace.add_constant(v_trail_element, trail_element)
        return v_trail_element

    def _get_field_out_variable(self, namespace: CascadeNamespace, field: OutputField) -> str:
        out_variable = f"r_{field.id}"
        namespace.register_var(out_variable)
        return out_variable

    def _get_field_extraction(self, state: GenState, field: OutputField) -> OutStatement:
        return (
            self._get_required_field_extraction(state, field)
            if field.is_required else
            self._get_optional_field_extraction(state, field)
        )

    def _get_required_field_extraction(self, state: GenState, field: OutputField) -> OutStatement:
        access_expr = self._get_access_expr(state.namespace, field)
        trail_element = self._get_trail_element_expr(state.namespace, field)

        if self._debug_trail == DebugTrail.DISABLE:
            return RawExpr(access_expr)

        out_variable = self._get_field_out_variable(state.namespace, field)
        stmt = (
            CodeBlock(
                """
                try:
                    <out_variable> = <access_expr>
                except Exception as e:
                    <error_handling>
                """,
                out_variable=RawExpr(out_variable),
                access_expr=RawExpr(access_expr),
                trail_element=RawExpr(trail_element),
            )
            if self._debug_trail == DebugTrail.ALL else
            CodeBlock(
                """
                try:
                    <out_variable> = <access_expr>
                except Exception as e:
                    append_trail(e, <trail_element>)
                    raise
                """,
                out_variable=RawExpr(out_variable),
                access_expr=RawExpr(access_expr),
                trail_element=RawExpr(trail_element),
            )
        )
        return OutVarStatement(
            stmt=statements(
                stmt,
                CodeBlock.EMPTY_LINE,
            ),
            var=out_variable,
        )

    def _get_optional_field_extraction(self, state: GenState, field: OutputField) -> OutStatement:
        access_expr = self._get_access_expr(state.namespace, field)
        out_variable = self._get_field_out_variable(state.namespace, field)

        def stmt_maker(*, on_access_ok: Statement, on_access_error: Statement) -> Statement:
            return statements(
                CodeBlock(
                    """
                    try:
                        <out_variable> = <access_expr>
                    except <access_error>:
                        <on_access_error>
                    else:
                        <on_access_ok>
                    """,
                    out_variable=RawExpr(out_variable),
                    access_expr=RawExpr(access_expr),
                    on_access_ok=on_access_ok,
                    on_access_error=on_access_error,
                ),
                CodeBlock.EMPTY_LINE,
            )
        return OptionalOutVarStatement(
            var=out_variable,
            stmt_maker=stmt_maker,
        )

    def _get_root_crown_stmt(self, state: GenState) -> RequiredStatement:
        if isinstance(self._name_layout.crown, OutDictCrown):
            result = self._get_dict_crown_out_stmt(state, self._name_layout.crown)
        elif isinstance(self._name_layout.crown, OutListCrown):
            result = self._get_list_crown_out_stmt(state, self._name_layout.crown)
        else:
            raise TypeError
        if isinstance(result, OptionalOutVarStatement):
            raise TypeError
        return result

    def _get_crown_out_stmt(self, state: GenState, key: CrownPathElem, crown: OutCrown) -> OutStatement:
        with state.add_key(key):
            if isinstance(crown, OutDictCrown):
                return self._get_dict_crown_out_stmt(state, crown)
            if isinstance(crown, OutListCrown):
                return self._get_list_crown_out_stmt(state, crown)
            if isinstance(crown, OutFieldCrown):
                return self._get_field_crown_out_stmt(state, crown)
            if isinstance(crown, OutNoneCrown):
                return self._get_none_crown_out_stmt(state, crown)
        raise TypeError

    def _get_dict_crown_out_stmt(self, state: GenState, crown: OutDictCrown) -> OutStatement:
        builder = DictBuilder()
        for key, sub_crown in crown.map.items():
            if key in crown.sieves:
                self._process_dict_sub_crown(
                    state=state,
                    builder=builder,
                    key=key,
                    sub_crown=sub_crown,
                    out_stmt=self._get_crown_out_stmt(state, key, sub_crown),
                )
            else:
                self._process_dict_sieved_sub_crown(
                    state=state,
                    builder=builder,
                    key=key,
                    sieve=crown.sieves[key],
                    sub_crown=sub_crown,
                    out_stmt=self._get_crown_out_stmt(state, key, sub_crown),
                )

        dict_literal = DictLiteral(builder.dict_items)
        if not builder.before_stmts and not builder.after_stmts:
            return dict_literal

        out_variable = state.v_crown
        state.namespace.register_var(out_variable)
        return OutVarStatement(
            stmt=statements(
                *builder.before_stmts,
                CodeBlock(
                    "<out_variable> = <main_dict>",
                    out_variable=RawExpr(out_variable),
                    main_dict=dict_literal,
                ),
                *builder.after_stmts,
            ),
            var=out_variable,
        )

    def _wrap_with_dumper_call(self, state: GenState, sub_crown: OutCrown, expr: Expression) -> RequiredStatement:
        if not isinstance(sub_crown, OutFieldCrown):
            return expr

        if self._fields_dumpers[sub_crown.id] == as_is_stub:
            return expr
        field = self._id_to_field[sub_crown.id]
        trail_element = self._get_trail_element_expr(state.namespace, field)
        dumper_call = CodeExpr(
            "<dumper>(<expr>)",
            dumper=RawExpr(self._v_dumper(field)),
            expr=expr,
        )
        out_variable = f"dumped_{field.id}"
        state.namespace.register_var(out_variable)

        if self._debug_trail == DebugTrail.ALL:
            wrapped = CodeBlock(
                """
                try:
                    <out_variable> = <dumper_call>
                except Exception as e:
                    raise error_handler(1, obj, append_trail(e, <trail_element>)) from None
                """,
                out_variable=RawExpr(out_variable),
                dumper_call=dumper_call,
                trail_element=RawExpr(trail_element),
            )
            return OutVarStatement(var=out_variable, stmt=wrapped)
        if self._debug_trail == DebugTrail.FIRST:
            wrapped = CodeBlock(
                """
                try:
                    <out_variable> = <dumper_call>
                except Exception as e:
                    append_trail(e, <trail_element>)
                    raise
                """,
                out_variable=RawExpr(out_variable),
                dumper_call=dumper_call,
                trail_element=RawExpr(trail_element),
            )
            return OutVarStatement(var=out_variable, stmt=wrapped)
        return dumper_call

    def _process_dict_sub_crown(
        self,
        state: GenState,
        builder: DictBuilder,
        key: str,
        sub_crown: OutCrown,
        out_stmt: OutStatement,
    ) -> None:
        if isinstance(out_stmt, Expression):
            dumper_call = self._wrap_with_dumper_call(
                state=state,
                sub_crown=sub_crown,
                expr=out_stmt,
            )
            if isinstance(dumper_call, Expression):
                builder.dict_items.append(DictKeyValue(StringLiteral(key), dumper_call))
            elif isinstance(dumper_call, OutVarStatement):
                builder.before_stmts.append(dumper_call.stmt)
                builder.dict_items.append(DictKeyValue(StringLiteral(key), RawExpr(dumper_call.var)))
            else:
                raise TypeError
        if isinstance(out_stmt, OutVarStatement):
            builder.before_stmts.append(out_stmt.stmt)
            self._process_dict_sub_crown(
                state=state,
                builder=builder,
                key=key,
                sub_crown=sub_crown,
                out_stmt=RawExpr(out_stmt.var),
            )
        if isinstance(out_stmt, OptionalOutVarStatement):
            stmt = out_stmt.stmt_maker(
                on_access_ok=self._get_dict_append(
                    state=state,
                    key=key,
                    sub_crown=sub_crown,
                    expr=RawExpr(out_stmt.var),
                ),
                on_access_error=CodeBlock.PASS,
            )
            builder.after_stmts.append(stmt)
        raise TypeError

    def _process_dict_sieved_sub_crown(
        self,
        state: GenState,
        builder: DictBuilder,
        key: str,
        sieve: Sieve,
        sub_crown: OutCrown,
        out_stmt: OutStatement,
    ) -> None:
        if isinstance(out_stmt, OptionalOutVarStatement):
            stmt = out_stmt.stmt_maker(
                on_access_ok=self._get_dict_sieved_append(
                    state=state,
                    sieve=sieve,
                    key=key,
                    sub_crown=sub_crown,
                    testing_var=out_stmt.var,
                ),
                on_access_error=CodeBlock.PASS,
            )
        elif isinstance(out_stmt, Expression):
            temp_var = state.var_suffix("temp", key)
            stmt = statements(
                CodeBlock(
                    "<temp_var> = <expr>",
                    temp_var=RawExpr(temp_var),
                    expr=out_stmt,
                ),
                self._get_dict_sieved_append(
                    state=state,
                    sieve=sieve,
                    key=key,
                    sub_crown=sub_crown,
                    testing_var=temp_var,
                ),
            )
        elif isinstance(out_stmt, OutVarStatement):
            stmt = self._get_dict_sieved_append(
                state=state,
                sieve=sieve,
                key=key,
                sub_crown=sub_crown,
                testing_var=out_stmt.var,
            )
        else:
            raise TypeError
        builder.after_stmts.append(stmt)

    def _get_dict_sieved_append(
        self,
        state: GenState,
        sieve: Sieve,
        key: str,
        sub_crown: OutCrown,
        testing_var: str,
    ) -> Statement:
        return CodeBlock(
            """
            if <condition>:
                <dict_append>
            """,
            condition=RawExpr(self._get_sieve_condition(state, sieve, key, testing_var)),
            dict_append=self._get_dict_append(state, key, sub_crown, RawExpr(testing_var)),
        )

    def _get_dict_append(
        self,
        state: GenState,
        key: str,
        sub_crown: OutCrown,
        expr: Expression,
    ) -> Statement:
        dumped = self._wrap_with_dumper_call(state, sub_crown, expr)
        if isinstance(dumped, OutVarStatement):
            return CodeBlock(
                """
                <dumper_call>
                <crown>[<key>] = <dumped_value>
                """,
                dumper_call=dumped.stmt,
                key=StringLiteral(key),
                crown=RawExpr(state.v_crown),
                dumped_value=RawExpr(dumped.var),
            )
        if isinstance(dumped, Expression):
            return CodeBlock(
                """
                <crown>[<key>] = <dumper_call>
                """,
                dumper_call=dumped,
                key=StringLiteral(key),
                crown=RawExpr(state.v_crown),
            )
        raise TypeError

    def _get_sieve_condition(self, state: GenState, sieve: Sieve, key: str, input_expr: str) -> str:
        default_clause = get_default_clause(sieve)
        if default_clause is None:
            v_sieve = state.suffix("sieve", key)
            state.namespace.add_constant(v_sieve, sieve)
            return f"{v_sieve}({input_expr})"

        if isinstance(default_clause, DefaultValue):
            literal_expr = get_literal_expr(default_clause.value)
            if literal_expr is not None:
                return (
                    f"{input_expr} is not {literal_expr}"
                    if is_singleton(default_clause.value) else
                    f"{input_expr} != {literal_expr}"
                )
            v_default = state.suffix("default", key)
            state.namespace.add_constant(v_default, default_clause.value)
            return f"{input_expr} != {v_default}"

        if isinstance(default_clause, DefaultFactory):
            literal_expr = get_literal_from_factory(default_clause.factory)
            if literal_expr is not None:
                return f"{input_expr} != {literal_expr}"
            v_default = state.suffix("default", key)
            state.namespace.add_constant(v_default, default_clause.factory)
            return f"{input_expr} != {v_default}()"

        if isinstance(default_clause, DefaultFactoryWithSelf):
            v_default = state.suffix("default", key)
            state.namespace.add_constant(v_default, default_clause.factory)
            return f"{input_expr} != {v_default}(data)"

        raise TypeError

    def _get_list_crown_out_stmt(self, state: GenState, crown: OutListCrown) -> OutStatement:
        out_stmts = [
            self._get_crown_out_stmt(state, idx, sub_crown)
            for idx, sub_crown in enumerate(crown.map)
        ]
        before_stmts = [
            out_stmt.stmt
            for out_stmt in out_stmts
            if isinstance(out_stmt, OutVarStatement)
        ]
        dumped_out_stmts = [
            self._wrap_with_dumper_call(
                state,
                sub_crown,
                out_stmt if isinstance(out_stmt, Expression) else RawExpr(out_stmt.var),
            )
            for sub_crown, out_stmt in zip(crown.map, out_stmts)
        ]
        before_stmts.extend(
            out_stmt.stmt
            for out_stmt in dumped_out_stmts
            if isinstance(out_stmt, OutVarStatement)
        )
        list_literal = ListLiteral(
            [
                out_stmt if isinstance(out_stmt, Expression) else RawExpr(out_stmt.var)
                for out_stmt in dumped_out_stmts
            ],
        )
        if not before_stmts:
            return list_literal

        out_variable = state.v_crown
        state.namespace.register_var(out_variable)
        return OutVarStatement(
            stmt=statements(
                *before_stmts,
                CodeBlock(
                    "<out_variable> = <list_literal>",
                    out_variable=RawExpr(out_variable),
                    list_literal=list_literal,
                ),
            ),
            var=out_variable,
        )

    def _get_field_crown_out_stmt(self, state: GenState, crown: OutFieldCrown) -> OutStatement:
        state.field_id_to_path[crown.id] = state.path
        return self._get_field_extraction(state, self._id_to_field[crown.id])

    def _get_none_crown_out_stmt(self, state: GenState, crown: OutNoneCrown) -> OutStatement:
        if isinstance(crown.placeholder, DefaultFactory):
            literal_expr = get_literal_from_factory(crown.placeholder.factory)
            if literal_expr is not None:
                return RawExpr(literal_expr)

            v_placeholder = state.suffix("placeholder")
            state.namespace.add_constant(v_placeholder, crown.placeholder.factory)
            return RawExpr(v_placeholder + "()")

        if isinstance(crown.placeholder, DefaultValue):
            literal_expr = get_literal_expr(crown.placeholder.value)
            if literal_expr is not None:
                return RawExpr(literal_expr)

            v_placeholder = state.suffix("placeholder")
            state.namespace.add_constant(v_placeholder, crown.placeholder.value)
            return RawExpr(v_placeholder)

        raise TypeError


class ModelOutputJSONSchemaGen:
    def __init__(
        self,
        shape: OutputShape,
        extra_move: OutExtraMove,
        field_json_schema_getter: Callable[[OutputField], JSONSchema],
        field_default_dumper: Callable[[OutputField], Omittable[JSONValue]],
        placeholder_dumper: Callable[[Any], JSONValue],
    ):
        self._shape = shape
        self._extra_move = extra_move
        self._field_json_schema_getter = field_json_schema_getter
        self._field_default_dumper = field_default_dumper
        self._placeholder_dumper = placeholder_dumper

    def _convert_dict_crown(self, crown: OutDictCrown) -> JSONSchema:
        return JSONSchema(
            type=JSONSchemaType.OBJECT,
            required=[
                key
                for key, value in crown.map.items()
                if self._is_required_crown(value)
            ],
            properties={
                key: self.convert_crown(value)
                for key, value in crown.map.items()
            },
            additional_properties=self._extra_move is not None,
        )

    def _convert_list_crown(self, crown: OutListCrown) -> JSONSchema:
        items = [
            self.convert_crown(sub_crown)
            for sub_crown in crown.map
        ]
        return JSONSchema(
            type=JSONSchemaType.ARRAY,
            prefix_items=items,
            max_items=len(items),
            min_items=len(items),
        )

    def _convert_field_crown(self, crown: OutFieldCrown) -> JSONSchema:
        field = self._shape.fields_dict[crown.id]
        json_schema = self._field_json_schema_getter(field)
        default = self._field_default_dumper(field)
        if default != Omitted():
            return replace(json_schema, default=default)
        return json_schema

    def _convert_none_crown(self, crown: OutNoneCrown) -> JSONSchema:
        value = (
            crown.placeholder.factory()
            if isinstance(crown.placeholder, DefaultFactory) else
            crown.placeholder.value
        )
        return JSONSchema(const=self._placeholder_dumper(value))

    def _is_required_crown(self, crown: OutCrown) -> bool:
        if isinstance(crown, OutFieldCrown):
            return self._shape.fields_dict[crown.id].is_required
        return True

    def convert_crown(self, crown: OutCrown) -> JSONSchema:
        if isinstance(crown, OutDictCrown):
            return self._convert_dict_crown(crown)
        if isinstance(crown, OutListCrown):
            return self._convert_list_crown(crown)
        if isinstance(crown, OutFieldCrown):
            return self._convert_field_crown(crown)
        if isinstance(crown, OutNoneCrown):
            return self._convert_none_crown(crown)
        raise TypeError
