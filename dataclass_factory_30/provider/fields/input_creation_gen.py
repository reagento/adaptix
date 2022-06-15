from .definitions import InputFigure, ExtraTargets, ExtraKwargs, ExtraSaturate, InputCreationGen, VarBinder
from ..request_cls import InputFieldRM, ParamKind
from ...code_tools import CodeBuilder, ContextNamespace


class BuiltinInputCreationGen(InputCreationGen):
    """Generator producing creation of desired object.

    It takes fields, extra and opt_fields from local vars to
    """

    def __init__(self, figure: InputFigure):
        self._figure = figure

    def _is_extra_target(self, field: InputFieldRM):
        return (
            isinstance(self._figure.extra, ExtraTargets)
            and
            field.name in self._figure.extra.fields
        )

    def generate_input_creation(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        has_opt_fields = any(
            fld.is_optional and not self._is_extra_target(fld)
            for fld in self._figure.fields
        )

        builder = CodeBuilder()
        ctx_namespace.add('constructor', self._figure.constructor)

        with builder("constructor("):
            for field in self._figure.fields:

                if self._is_extra_target(field):
                    value = binder.extra
                elif field.is_required:
                    value = binder.field(field)
                else:
                    continue

                if field.param_kind == ParamKind.KW_ONLY:
                    builder(f"{field.name}={value},")
                else:
                    builder(f"{value},")

            if has_opt_fields:
                builder(f"**{binder.opt_fields}")

            if self._figure.extra == ExtraKwargs():
                builder(f"**{binder.extra}")

        builder += ")"

        if isinstance(self._figure.extra, ExtraSaturate):
            ctx_namespace.add('saturator', self._figure.extra.func)

            out_builder = CodeBuilder() + 'result = ' << builder.string()
            out_builder += f"saturator(result, {binder.extra})"
            return out_builder

        return CodeBuilder() << "return " << builder.string()
