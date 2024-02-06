from abc import ABC, abstractmethod
from typing import AbstractSet, Mapping, Optional, Set

from .utils import NAME_TO_BUILTIN


class CascadeNamespace(ABC):
    @abstractmethod
    def add_constant(self, name: str, value: object) -> None:
        ...

    @abstractmethod
    def try_add_constant(self, name: str, value: object) -> bool:
        ...

    @abstractmethod
    def register_var(self, name: str) -> None:
        ...

    @abstractmethod
    def try_register_var(self, name: str) -> bool:
        ...


class BuiltinCascadeNamespace(CascadeNamespace):
    __slots__ = ('_constants', '_occupied', '_variables', '_allow_builtins')

    def __init__(
        self,
        constants: Optional[Mapping[str, object]] = None,
        occupied: Optional[AbstractSet[str]] = None,
        allow_builtins: bool = False,
    ):
        self._constants = {} if constants is None else dict(constants)
        self._occupied = set() if occupied is None else occupied
        self._variables: Set[str] = set()
        self._allow_builtins = allow_builtins

    def try_add_constant(self, name: str, value: object) -> bool:
        if (
            name in self._occupied
            or name in self._variables
            or (name in NAME_TO_BUILTIN and not self._allow_builtins)
        ):
            return False
        if name in self._constants:
            return value is self._constants[name]
        self._constants[name] = value
        return True

    def try_register_var(self, name: str) -> bool:
        if (
            name in self._occupied
            or name in self._constants
            or name in self._variables
            or (name in NAME_TO_BUILTIN and not self._allow_builtins)
        ):
            return False
        self._variables.add(name)
        return True

    def add_constant(self, name: str, value: object) -> None:
        if not self.try_add_constant(name, value):
            raise KeyError(f"Key {name} is duplicated")

    def register_var(self, name: str) -> None:
        if not self.try_register_var(name):
            raise KeyError(f"Key {name} is duplicated")

    @property
    def constants(self) -> Mapping[str, object]:
        return self._constants
