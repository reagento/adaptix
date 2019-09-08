from typing import Any, Callable, TypeVar

T = TypeVar("T")
K = TypeVar("K")
Serializer = Callable[[T], Any]
Parser = Callable[[Any], T]
InnerConverter = Callable[[T], T]
