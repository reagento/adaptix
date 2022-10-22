from string import Template
from typing import Dict, Mapping

from ...code_tools import CodeBuilder, ContextNamespace, get_literal_expr
from ...common import Dumper
from ...model_tools import AttrAccessor, ItemAccessor, OutputField, OutputFigure
from ...struct_path import append_path, extend_path
from .crown_definitions import ExtraExtract, ExtraTargets, OutExtraMove
from .definitions import CodeGenerator, VarBinder


class BuiltinOutputExtractionGen(CodeGenerator):
    def __init__(
        self,
        figure: OutputFigure,
        extra_move: OutExtraMove,
        debug_path: bool,
        fields_dumpers: Mapping[str, Dumper],
    ):
        self._figure = figure
        self._extra_move = extra_move
        self._debug_path = debug_path
        self._fields_dumpers = fields_dumpers
        self._extra_targets = (
            self._extra_move.fields
            if isinstance(self._extra_move, ExtraTargets)
            else ()
        )

    def __call__(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        builder = CodeBuilder()

        ctx_namespace.add("append_path", append_path)
        ctx_namespace.add("extend_path", extend_path)
        name_to_fields = {field.name: field for field in self._figure.fields}

        for field_name, dumper in self._fields_dumpers.items():
            ctx_namespace.add(self._dumper(name_to_fields[field_name]), dumper)

        if any(field.is_optional for field in self._figure.fields):
            builder(f"{binder.opt_fields} = {{}}")
            builder.empty_line()

        for field in self._figure.fields:
            if not self._is_extra_target(field):
                self._gen_field_extraction(
                    builder, binder, ctx_namespace, field,
                    on_access_error="pass",
                    on_access_ok_req=f"{binder.field(field)} = $expr",
                    on_access_ok_opt=f"{binder.opt_fields}[{field.name!r}] = $expr",
                )

        self._gen_extra_extraction(
            builder, binder, ctx_namespace, name_to_fields,
        )

        return builder

    def _is_extra_target(self, field: OutputField) -> bool:
        return field.name in self._extra_targets

    def _dumper(self, field: OutputField) -> str:
        return f"dumper_{field.name}"

    def _raw_field(self, field: OutputField) -> str:
        return f"r_{field.name}"

    def _accessor_getter(self, field: OutputField) -> str:
        return f"accessor_getter_{field.name}"

    def _gen_access_expr(self, binder: VarBinder, ctx_namespace: ContextNamespace, field: OutputField) -> str:
        accessor = field.accessor
        if isinstance(accessor, AttrAccessor):
            if accessor.attr_name.isidentifier():
                return f"{binder.data}.{accessor.attr_name}"
            return f"getattr({binder.data}, {accessor.attr_name!r})"
        if isinstance(accessor, ItemAccessor):
            return f"{binder.data}[{accessor.item_name!r}]"

        accessor_getter = self._accessor_getter(field)
        ctx_namespace.add(accessor_getter, field.accessor.getter)
        return f"{accessor_getter}({binder.data})"

    def _get_path_element_var_name(self, field: OutputField) -> str:
        return f"path_element_{field.name}"

    def _gen_path_element_expr(self, ctx_namespace: ContextNamespace, field: OutputField) -> str:
        path_element = field.accessor.path_element
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

        dumper = self._dumper(field)
        on_access_ok_stmt = Template(on_access_ok).substitute(expr=f"{dumper}({raw_access_expr})")

        if self._debug_path:
            builder += f"""
                try:
                    {on_access_ok_stmt}
                except Exception as e:
                    append_path(e, {path_element_expr})
                    raise e
            """
        else:
            builder += on_access_ok_stmt

        builder.empty_line()

    def _get_access_error_var_name(self, field: OutputField) -> str:
        return f"access_error_{field.name}"

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

        dumper = self._dumper(field)
        raw_field = self._raw_field(field)

        on_access_ok_stmt = Template(on_access_ok).substitute(
            expr=f"{dumper}({raw_field})"
        )

        access_error = field.accessor.access_error
        access_error_var = get_literal_expr(access_error)
        if access_error_var is None:
            access_error_var = self._get_access_error_var_name(field)
            ctx_namespace.add(access_error_var, access_error)

        if self._debug_path:
            builder += f"""
                try:
                    {raw_field} = {raw_access_expr}
                except {access_error_var}:
                    {on_access_error}
                else:
                    try:
                        {on_access_ok_stmt}
                    except Exception as e:
                        append_path(e, {path_element_expr})
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
        if isinstance(self._extra_move, ExtraTargets):
            self._gen_extra_target_extraction(builder, binder, ctx_namespace, name_to_fields)
        elif isinstance(self._extra_move, ExtraExtract):
            self._gen_extra_extract_extraction(builder, binder, ctx_namespace, self._extra_move)
        elif self._extra_move is not None:
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
            for field_name in self._extra_targets:
                field = name_to_fields[field_name]

                self._gen_required_field_extraction(
                    builder, binder, ctx_namespace, field,
                    on_access_ok=f"{binder.field(field)} = $expr",
                )

            builder += f'{binder.extra} = {{'
            builder <<= ", ".join(
                "**" + binder.field(name_to_fields[field_name])
                for field_name in self._extra_targets
            )
            builder <<= '}'
        else:
            extra_stack = self._get_extra_stack_name()

            builder += f"{extra_stack} = []"

            for field_name in self._extra_targets:
                field = name_to_fields[field_name]

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
