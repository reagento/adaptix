from dataclasses import astuple
from typing import Dict, Type, Any, Optional, TypeVar

from .common import Serializer, Parser
from .parsers import create_parser, get_lazy_parser
from .schema import Schema, merge_schema
from .serializers import create_serializer, get_lazy_serializer

DEFAULT_SCHEMA = Schema[Any](
    trim_trailing_underscore=True,
    skip_internal=True,
    only_mapped=False,
)


class StackedFactory:
    __slots__ = ("stack", "factory")

    def __init__(self, factory):
        self.stack = []
        self.factory = factory

    def parser(self, class_: Type):
        if class_ in self.stack:
            return get_lazy_parser(self.factory, class_)
        self.stack.append(class_)
        try:
            return self.factory._parser_with_stack(class_, self)
        finally:
            self.stack.pop()

    def serializer(self, class_: Type):
        if class_ in self.stack:
            return get_lazy_serializer(self.factory)
        self.stack.append(class_)
        try:
            return self.factory._serializer_with_stack(class_, self)
        finally:
            self.stack.pop()


T = TypeVar("T")


class Factory:
    __slots__ = ("default_schema", "debug_path", "schemas")

    def __init__(self,
                 default_schema: Optional[Schema] = None,
                 schemas: Optional[Dict[Type, Schema]] = None,
                 debug_path: bool = False):
        self.default_schema = merge_schema(default_schema, DEFAULT_SCHEMA)
        self.debug_path = debug_path
        self.schemas: Dict[Type, Schema] = {}
        if schemas:
            self.schemas.update({
                type_: merge_schema(schema, self.default_schema)
                for type_, schema in schemas.items()
            })

    def schema(self, class_: Type[T]) -> Schema[T]:
        schema = self.schemas.get(class_)
        if not schema:
            schema = Schema(
                *astuple(self.default_schema)
            )
            self.schemas[class_] = schema
        return schema

    def parser(self, class_: Type[T]) -> Parser[T]:
        return self._parser_with_stack(class_, StackedFactory(self))

    def _parser_with_stack(self, class_: Type[T], stacked_factory: StackedFactory) -> Parser[T]:
        schema = self.schema(class_)
        if not schema.parser:
            schema.parser = create_parser(stacked_factory, schema, self.debug_path, class_)
        return schema.parser

    def serializer(self, class_: Type[T]) -> Serializer[T]:
        return self._serializer_with_stack(class_, StackedFactory(self))

    def _serializer_with_stack(self, class_: Type[T], stacked_factory: StackedFactory) -> Serializer[T]:
        schema = self.schema(class_)
        if not schema.serializer:
            schema.serializer = create_serializer(stacked_factory, schema, self.debug_path, class_)
        return schema.serializer

    def load(self, data: Any, class_: Type[T]) -> T:
        return self.parser(class_)(data)

    def dump(self, data: T, class_: Type[T] = None) -> Any:
        if class_ is None:
            class_ = type(data)
        return self.serializer(class_)(data)
