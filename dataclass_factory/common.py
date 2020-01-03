from typing import Any, Callable, TypeVar, Type
from .factory import AbstractFactory

T = TypeVar("T")
K = TypeVar("K")

Serializer = Callable[[T], Any]
SerializerGetter = Callable[
    [Type[T], AbstractFactory, bool],
    Serializer
]

Parser = Callable[[Any], T]
ParserGetter = Callable[
    [Type[T], AbstractFactory, bool],
    Parser
]
InnerConverter = Callable[[T], T]
