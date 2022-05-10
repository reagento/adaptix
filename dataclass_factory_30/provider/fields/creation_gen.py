from dataclass_factory_30.code_tools import CodeBuilder
from dataclass_factory_30.code_tools.name_allocator import NameAllocator
from dataclass_factory_30.provider import InputFigure, ExtraTargets, ExtraKwargs
from dataclass_factory_30.provider.fields.basic_gen import VarBinder
from dataclass_factory_30.provider.fields.definitions import ExtraSaturate
from dataclass_factory_30.provider.request_cls import InputFieldRM, ParamKind


class CreationGen:
    """Generator producing creation of desired object.

    It takes fields, extra and opt_fields from local vars to
    """

    def __init__(self, figure: InputFigure, binder: VarBinder, name_allocator: NameAllocator):
        self._figure = figure
        self._binder = binder
        self._allocator = name_allocator

    def _is_extra_target(self, field: InputFieldRM):
        return (
            isinstance(self._figure.extra, ExtraTargets)
            and
            field.name in self._figure.extra.fields
        )

    def generate(self) -> CodeBuilder:
        has_opt_fields = any(
            fld.is_optional and not self._is_extra_target(fld)
            for fld in self._figure.fields
        )

        builder = CodeBuilder()
        constructor = self._allocator.alloc_outer(self._figure.constructor, 'constructor')
        builder += f"{constructor}("

        with builder:
            for field in self._figure.fields:

                if self._is_extra_target(field):
                    value = self._binder.extra
                elif field.is_required:
                    value = self._binder.field(field)
                else:
                    continue

                if field.param_kind == ParamKind.KW_ONLY:
                    builder(f"{field.name}={value},")
                else:
                    builder(f"{value},")

            if has_opt_fields:
                builder(f"**{self._binder.opt_fields}")

            if self._figure.extra == ExtraKwargs():
                builder(f"**{self._binder.extra}")

        builder += ")"

        if isinstance(self._figure.extra, ExtraSaturate):
            saturator = self._allocator.alloc_outer(self._figure.extra.func, 'saturator')
            result = self._allocator.alloc_local('result')

            out_builder = CodeBuilder() + result << " = " << builder.string()
            out_builder += f"{saturator}({result}, {self._binder.extra})"
            return out_builder

        return CodeBuilder() << "return " << builder.string()
