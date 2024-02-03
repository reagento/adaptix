from abc import ABC, abstractmethod
from typing import AbstractSet, Dict, Optional


class ContextNamespace(ABC):
    @abstractmethod
    def add(self, name: str, value: object) -> None:
        ...

    @abstractmethod
    def try_add(self, name: str, value: object) -> bool:
        ...


class BuiltinContextNamespace(ContextNamespace):
    __slots__ = ('dict', '_occupied')

    def __init__(
        self,
        namespace: Optional[Dict[str, object]] = None,
        occupied: Optional[AbstractSet[str]] = None,
    ):
        if namespace is None:
            namespace = {}
        if occupied is None:
            occupied = set()

        self.dict = namespace
        self._occupied = occupied

    def add(self, name: str, value: object) -> None:
        if not self.try_add(name, value):
            raise KeyError(f"Key {name} is duplicated")

    def try_add(self, name: str, value: object) -> bool:
        if name in self._occupied:
            return False
        if name in self.dict:
            return value is self.dict[name]
        self.dict[name] = value
        return True
