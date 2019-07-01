from typing import Any, Callable, TypeVar

T = TypeVar("T")
Serializer = Callable[[T], Any]
Parser = Callable[[Any], T]
