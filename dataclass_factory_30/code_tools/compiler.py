from abc import ABC, abstractmethod
from typing import Callable, Dict, Any

from .code_builder import CodeBuilder


class ClosureCompiler(ABC):
    """
    Abstract class compiling closures
    """

    @abstractmethod
    def compile(self, builder: CodeBuilder, filename: str, namespace: Dict[str, Any]) -> Callable:
        """
        Execute content of builder and return value that body returned (it is must be a closure).
        :param builder: Builder containing body of function that create closure
        :param filename: virtual name of file there code is located
        :param namespace: Global variables
        :return: closure object
        """


class BasicClosureCompiler(ClosureCompiler):
    def _make_source(self, builder: CodeBuilder):
        main_builder = CodeBuilder()

        main_builder += "def closure_maker():"
        with main_builder:
            main_builder.extend(builder)

        return main_builder.string()

    def compile(self, builder: CodeBuilder, filename: str, namespace: Dict[str, Any]) -> Callable:
        source = self._make_source(builder)

        code_obj = compile(source, filename, "exec")

        local_namespace: Dict[str, Any] = {}
        exec(code_obj, namespace, local_namespace)  # noqa

        return local_namespace["closure_maker"]()


class SavingClosureCompiler(BasicClosureCompiler):
    def __init__(self):
        self.source = ""

    def _make_source(self, builder: CodeBuilder):
        self.source = super()._make_source(builder)
        return self.source
