from copy import copy
from typing import Any, Dict, Optional, Type, TypeVar

from .common import AbstractFactory, Parser, Serializer
from .jsonschema import create_schema
from .naming import NameStyle
from .parsers import create_parser, get_lazy_parser
from .schema import merge_schema, Schema, Unknown
from .serializers import create_serializer, get_lazy_serializer
from .type_detection import is_generic_concrete
from .schema_helpers import COMMON_SCHEMAS

DEFAULT_SCHEMA = Schema[Any](
    trim_trailing_underscore=True,
    skip_internal=True,
    only_mapped=False,
    name_style=NameStyle.ignore,
    unknown=Unknown.SKIP,
)


class StackedFactory(AbstractFactory):
    __slots__ = ("stack", "factory")

    def __init__(self, factory):
        self.stack = []
        self.factory = factory

    def json_schema_ref_name(self, class_: Type):
        return self.factory._json_schema_ref_name_with_stack(class_, self)

    def json_schema(self, class_: Type):
        if class_ in self.stack:
            return
        self.stack.append(class_)
        try:
            return self.factory._json_schema_with_stack(class_, self)
        finally:
            self.stack.pop()

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
    def __init__(self,
                 default_schema: Optional[Schema] = None,
                 schemas: Optional[Dict[Type, Schema]] = None,
                 debug_path: bool = False):
        self.debug_path = debug_path
        self.default_schema = default_schema
        self.schemas: Dict[Type, Schema] = COMMON_SCHEMAS.copy()
        if schemas:
            self.schemas.update({
                type_: merge_schema(schema, self.default_schema, DEFAULT_SCHEMA)
                for type_, schema in schemas.items()
            })
        self.json_schemas: Dict[str, Dict] = {}
        self.json_schema_names: Dict[str, Type] = {}

    def schema(self, class_: Type[T]) -> Schema[T]:
        if is_generic_concrete(class_):
            base_class = class_.__origin__  # type: ignore
        else:
            base_class = None

        schema = self.schemas.get(class_)
        if not schema:
            if base_class:
                schema = self.schemas.get(base_class)
            if not schema:
                schema = Schema()
            schema = merge_schema(schema, self.default_schema, DEFAULT_SCHEMA)
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

    def json_schema_ref_name(self, class_: Type[T]):
        return self._json_schema_ref_name_with_stack(class_, StackedFactory(self))

    def _json_schema_ref_name_with_stack(self, class_: Type[T], stacked_factory: StackedFactory):
        schema = self.schema(class_)
        if schema.name is not None:
            if schema.name not in self.json_schema_names:
                return schema.name
            if self.json_schema_names[schema.name] != class_:
                raise ValueError(f"Already found type with name `{schema.name}`: "
                                 f"{self.json_schema_names[schema.name]}. "
                                 f"Please, specify another name for {class_}")
            return schema.name
        name = getattr(class_, "__qualname__", "") or getattr(class_, "__name__", "") or str(class_)
        if name in self.json_schema_names:
            raise ValueError(f"Already found type with name `{name}`: "
                             f"{self.json_schema_names[name]}. "
                             f"Please, specify another name for {class_} "
                             f"in schema or rename class itself")
        schema.name = name
        stacked_factory.json_schema(class_)
        return name

    def json_schema(self, class_: Type[T]) -> Dict[str, Any]:
        return self._json_schema_with_stack(class_, StackedFactory(self))

    def json_schema_definitions(self) -> Dict[str, Any]:
        return {
            "definitions": {
                k: v
                for k, v in self.json_schemas.items()
            },
        }

    def _json_schema_with_stack(self, class_: Type[T], stacked_factory: StackedFactory) -> Dict[str, Any]:
        schema = self.schema(class_)
        name = self._json_schema_ref_name_with_stack(class_, stacked_factory)
        if name in self.json_schemas:
            return self.json_schemas[name]
        json_schema = create_schema(stacked_factory, schema, class_)
        self.json_schemas[name] = json_schema
        return json_schema

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
