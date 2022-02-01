from typing import Any, Callable, Type, TypeVar


T = TypeVar("T")
K = TypeVar("K")


class AbstractFactory:
    """
    Facade class to retrieve data converters
    """
    def parser(self, class_: Type):
        raise NotImplementedError

    def serializer(self, class_: Type):
        raise NotImplementedError

    def json_schema(self, class_: Type):
        raise NotImplementedError

    def json_schema_ref_name(self, class_: Type):
        raise NotImplementedError


Serializer = Callable[[T], Any]
SerializerGetter = Callable[
    [Type[T], AbstractFactory, bool],
    Serializer,
]

Parser = Callable[[Any], T]
ParserGetter = Callable[
    [Type[T], AbstractFactory, bool],
    Parser[T],
]
InnerConverter = Callable[[T], T]
