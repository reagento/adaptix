from typing import Dict


class ContextNamespace:
    def __init__(self, namespace: Dict[str, object]):
        self._namespace = namespace

    def add(self, name: str, value: object) -> None:
        if name in self._namespace:
            raise KeyError("Key duplication")

        self._namespace[name] = value

