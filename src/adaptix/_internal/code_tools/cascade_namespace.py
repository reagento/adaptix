from abc import ABC, abstractmethod
from typing import AbstractSet, Mapping, Optional, Set


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
    __slots__ = ('_constants', '_occupied', '_variables')

    def __init__(
        self,
        constants: Optional[Mapping[str, object]] = None,
        occupied: Optional[AbstractSet[str]] = None,
    ):
        self._constants = {} if constants is None else dict(constants)
        self._occupied = set() if occupied is None else occupied
        self._variables: Set[str] = set()

    def try_add_constant(self, name: str, value: object) -> bool:
        if name in self._occupied or name in self._variables:
            return False
        if name in self._constants:
            return value is self._constants[name]
        self._constants[name] = value
        return True

    def try_register_var(self, name: str) -> bool:
        if name in self._occupied or name in self._constants or name in self._variables:
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
