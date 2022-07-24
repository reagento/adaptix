import sys
from abc import ABC, abstractmethod
from textwrap import dedent

from .common import VarTuple


def _true():
    return True


def _false():
    return False


class Requirement(ABC):
    __slots__ = ('is_meet', '__bool__', '__dict__')

    def __init__(self):
        self.is_meet = self._evaluate()
        self.__bool__ = _true if self.is_meet else _false

    @abstractmethod
    def _evaluate(self) -> bool:
        pass


class PythonVersionRequirement(Requirement):
    def __init__(self, min_version: VarTuple[int]):
        self.min_version = min_version
        super().__init__()

    def _evaluate(self) -> bool:
        return sys.version_info >= self.min_version


class PackageRequirement(Requirement):
    def __init__(self, package: str, test_stmt: str):
        self.package = package
        self.test_stmt = dedent(test_stmt)
        super().__init__()

    def _evaluate(self) -> bool:
        try:
            # pylint: disable=exec-used
            exec(self.test_stmt)  # noqa
        except ImportError:
            return False
        return True


HAS_PY_39 = PythonVersionRequirement((3, 9))
HAS_ANNOTATED = HAS_PY_39
HAS_STD_CLASSES_GENERICS = HAS_PY_39

HAS_ATTRS_PKG = PackageRequirement('attrs', 'from attrs import fields')