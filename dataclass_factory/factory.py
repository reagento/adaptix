from copy import copy
from typing import Dict, Type, Any, Optional, TypeVar

from .common import Serializer, Parser, AbstractFactory
from .parsers import create_parser, get_lazy_parser
from .schema import Schema, merge_schema
from .serializers import create_serializer, get_lazy_serializer
from .type_detection import is_generic_concrete

DEFAULT_SCHEMA = Schema[Any](
    trim_trailing_underscore=True,
    skip_internal=True,
    only_mapped=False,
)


class StackedFactory(AbstractFactory):
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


class Factory(AbstractFactory):
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
        if is_generic_concrete(class_):
            base_class = class_.__origin__  # type: ignore
        else:
            base_class = None

        schema = self.schemas.get(class_)
        if not schema:
            if base_class:
                schema = self.schemas.get(base_class)
            schema = merge_schema(schema, self.default_schema)
            self.schemas[class_] = schema
        return schema

    def parser(self, class_: Type[T]) -> Parser[T]:
        return self._parser_with_stack(class_, StackedFactory(self))

    def _parser_with_stack(self, class_: Type[T], stacked_factory: StackedFactory) -> Parser[T]:
        schema = self.schema(class_)

        if schema.get_parser is not None:
            if schema.parser is not None:
                raise TypeError("Schema can not have parser and get_parser at same time")
            else:
                new_schema = copy(schema)
                new_schema.parser = schema.get_parser(class_, stacked_factory, self.debug_path)
                new_schema.get_parser = None
                self.schemas[class_] = new_schema
                schema = new_schema

        if not schema.parser:
            schema.parser = create_parser(stacked_factory, schema, self.debug_path, class_)
        return schema.parser

    def serializer(self, class_: Type[T]) -> Serializer[T]:
        return self._serializer_with_stack(class_, StackedFactory(self))

    def _serializer_with_stack(self, class_: Type[T], stacked_factory: StackedFactory) -> Serializer[T]:
        schema = self.schema(class_)

        if schema.get_serializer is not None:
            if schema.serializer is not None:
                raise TypeError("Schema can not have serializer and get_serializer at same time")
            else:
                new_schema = copy(schema)
                new_schema.serializer = schema.get_serializer(class_, stacked_factory, self.debug_path)
                new_schema.get_serializer = None
                self.schemas[class_] = new_schema
                schema = new_schema

        if not schema.serializer:
            schema.serializer = create_serializer(stacked_factory, schema, self.debug_path, class_)

        return schema.serializer

    def load(self, data: Any, class_: Type[T]) -> T:
        return self.parser(class_)(data)

    def dump(self, data: T, class_: Type[T] = None) -> Any:
        if class_ is None:
            class_ = type(data)
        return self.serializer(class_)(data)
