from abc import ABC, abstractmethod
from typing import AbstractSet, Dict, Optional


class ContextNamespace(ABC):
    @abstractmethod
    def add(self, name: str, value: object) -> None:
        ...

    @abstractmethod
    def __contains__(self, item: str) -> bool:
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
        if name in self._occupied:
            raise KeyError(f"Key {name} is duplicated")
        if name in self.dict:
            if value is self.dict[name]:
                return
            raise KeyError(f"Key {name} is duplicated")
        self.dict[name] = value

    def __contains__(self, item: str) -> bool:
        return item in self.dict or item in self._occupied
