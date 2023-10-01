from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from ...code_tools.code_builder import CodeBuilder
from ...code_tools.context_namespace import ContextNamespace
from ...code_tools.prefix_mangler import MangledConstant, PrefixManglerBase, mangling_method
from ...model_tools.definitions import BaseField, InputShape, OutputShape
from ..request_cls import LocatedRequest

T = TypeVar('T')


@dataclass(frozen=True)
class InputShapeRequest(LocatedRequest[InputShape]):
    pass


@dataclass(frozen=True)
class OutputShapeRequest(LocatedRequest[OutputShape]):
    pass


class VarBinder(PrefixManglerBase):
    data = MangledConstant("data")
    extra = MangledConstant("extra")
    opt_fields = MangledConstant("opt_fields")

    @mangling_method(prefix="field_")
    def field(self, field: BaseField) -> str:
        return field.id


class CodeGenerator(ABC):
    @abstractmethod
    def produce_code(self, binder: VarBinder, ctx_namespace: ContextNamespace) -> CodeBuilder:
        ...
