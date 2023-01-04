# pylint: disable=exec-used
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from .code_builder import CodeBuilder


class ClosureCompiler(ABC):
    """Abstract class compiling closures"""

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
    def _make_source_builder(self, builder: CodeBuilder) -> CodeBuilder:
        main_builder = CodeBuilder()

        main_builder += "def _closure_maker():"
        with main_builder:
            main_builder.extend(builder)

        return main_builder

    def _compile(self, source: str, filename: str, namespace: Dict[str, Any]):
        code_obj = compile(source, filename, "exec")  # noqa: DUO110

        local_namespace: Dict[str, Any] = {}
        exec(code_obj, namespace, local_namespace)  # noqa: DUO105

        return local_namespace["_closure_maker"]()

    def compile(self, builder: CodeBuilder, filename: str, namespace: Dict[str, Any]) -> Callable:
        source = self._make_source_builder(builder).string()
        return self._compile(source, filename, namespace)
