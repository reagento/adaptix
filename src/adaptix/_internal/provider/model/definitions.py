from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from ...code_tools.code_builder import CodeBuilder
from ...code_tools.context_namespace import ContextNamespace
from ...model_tools.definitions import InputShape, OutputShape
from ..request_cls import LocatedRequest

T = TypeVar('T')


@dataclass(frozen=True)
class InputShapeRequest(LocatedRequest[InputShape]):
    pass


@dataclass(frozen=True)
class OutputShapeRequest(LocatedRequest[OutputShape]):
    pass


class CodeGenerator(ABC):
    @abstractmethod
    def produce_code(self, ctx_namespace: ContextNamespace) -> CodeBuilder:
        ...
