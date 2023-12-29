from abc import ABC, abstractmethod

from .code_tools.code_builder import CodeBuilder
from .code_tools.context_namespace import ContextNamespace


class CodeGenerator(ABC):
    @abstractmethod
    def produce_code(self, ctx_namespace: ContextNamespace) -> CodeBuilder:
        ...
