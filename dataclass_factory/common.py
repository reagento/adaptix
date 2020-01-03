from typing import Any, Callable, TypeVar, Type

T = TypeVar("T")
K = TypeVar("K")


class AbstractFactory:
    def parser(self, class_: Type):
        raise NotImplementedError

    def serializer(self, class_: Type):
        raise NotImplementedError


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
