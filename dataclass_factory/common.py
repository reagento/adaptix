from typing import Any, Callable, TypeVar, Type

T = TypeVar("T")
K = TypeVar("K")

Serializer = Callable[[T], Any]
SerializerCreate = Callable[[Type[T], bool], Serializer]

Parser = Callable[[Any], T]
ParserCreate = Callable[[Type[T], bool], Parser]

InnerConverter = Callable[[T], T]
