from dataclasses import dataclass
from typing import Protocol, TypeVar

from ...code_tools import CodeBuilder, ContextNamespace, MangledConstant, PrefixManglerBase, mangling_method
from ...model_tools import BaseField, InputFigure, OutputFigure
from ..request_cls import LocatedRequest

T = TypeVar('T')


@dataclass(frozen=True)
class InputFigureRequest(LocatedRequest[InputFigure]):
    pass


@dataclass(frozen=True)
class OutputFigureRequest(LocatedRequest[OutputFigure]):
    pass


class VarBinder(PrefixManglerBase):
    data = MangledConstant("data")
    extra = MangledConstant("extra")
    opt_fields = MangledConstant("opt_fields")

    @mangling_method("field_")
    def field(self, field: BaseField) -> str:
        return field.name


class CodeGenerator(Protocol):
    def __call__(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        ...
