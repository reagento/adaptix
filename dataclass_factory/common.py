from typing import Any, Callable

Serializer = Callable[[Any], Any]
Parser = Callable[[Any], Any]
