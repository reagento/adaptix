from typing import Any, Callable, TypeVar, Type
from .factory import StackedFactory

T = TypeVar("T")
K = TypeVar("K")

Serializer = Callable[[T], Any]
SerializerGetter = Callable[
    [Type[T], StackedFactory, bool],
    Serializer
]

Parser = Callable[[Any], T]
ParserGetter = Callable[
    [Type[T], StackedFactory, bool],
    Parser
]
InnerConverter = Callable[[T], T]
