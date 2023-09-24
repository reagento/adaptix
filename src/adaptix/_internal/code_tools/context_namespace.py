from abc import ABC, abstractmethod
from typing import Dict, Optional


class ContextNamespace(ABC):
    @abstractmethod
    def add(self, name: str, value: object) -> None:
        ...


class BuiltinContextNamespace(ContextNamespace):
    def __init__(self, namespace: Optional[Dict[str, object]] = None):
        if namespace is None:
            namespace = {}

        self.dict = namespace

    def add(self, name: str, value: object) -> None:
        if name in self.dict:
            if value is self.dict[name]:
                return
            raise KeyError(f"Key {name} is duplicated")

        self.dict[name] = value
