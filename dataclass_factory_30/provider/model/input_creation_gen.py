from ...code_tools import CodeBuilder, ContextNamespace
from ...model_tools import InputField, ParamKind
from .crown_definitions import ExtraKwargs, ExtraSaturate, ExtraTargets, InpExtraMove
from .definitions import CodeGenerator, InputFigure, VarBinder


class BuiltinInputCreationGen(CodeGenerator):
    """Generator producing creation of desired object.

    It takes fields, extra and opt_fields from local vars to
    """

    def __init__(self, figure: InputFigure, extra_move: InpExtraMove):
        self._figure = figure
        self._extra_move = extra_move

    def _is_extra_target(self, field: InputField):
        return (
            isinstance(self._extra_move, ExtraTargets)
            and
            field.name in self._extra_move.fields
        )

    def __call__(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        has_opt_fields = any(
            fld.is_optional and not self._is_extra_target(fld)
            for fld in self._figure.fields
        )

        builder = CodeBuilder()
        ctx_namespace.add('constructor', self._figure.constructor)

        with builder("constructor("):
            for field in self._figure.fields:

                if field.is_required or self._is_extra_target(field):
                    value = binder.field(field)
                else:
                    continue

                if field.param_kind == ParamKind.KW_ONLY:
                    builder(f"{field.param_name}={value},")
                else:
                    builder(f"{value},")

            if has_opt_fields:
                builder(f"**{binder.opt_fields},")

            if self._extra_move == ExtraKwargs():
                builder(f"**{binder.extra},")

        builder += ")"

        if isinstance(self._extra_move, ExtraSaturate):
            ctx_namespace.add('saturator', self._extra_move.func)

            out_builder = CodeBuilder() + 'result = ' << builder.string()
            out_builder += f"saturator(result, {binder.extra})"
            out_builder += "return result"
            return out_builder

        return CodeBuilder() << "return " << builder.string()
