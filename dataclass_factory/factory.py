from collections import defaultdict
from copy import copy

from typing import Dict, Type, Any, Optional

from .common import Serializer, Parser
from .parsers import create_parser
from .schema import Schema, merge_schema
from .serializers import create_serializer

DEFAULT_SCHEMA = Schema(
    trim_trailing_underscore=True,
    skip_internal=True,
    only_mapped=False,
)


class Factory:
    def __init__(self,
                 default_schema: Optional[Schema] = None,
                 schemas: Optional[Dict[Type, Schema]] = None,
                 debug_path: bool = False):
        self.default_schema = merge_schema(default_schema, DEFAULT_SCHEMA)
        self.debug_path = debug_path
        self.schemas: Dict[Type, Schema] = defaultdict(lambda: copy(self.default_schema))
        if schemas:
            self.schemas.update({
                type_: merge_schema(schema, self.default_schema)
                for type_, schema in schemas.items()
            })

    def schema(self, class_: Type) -> Schema:
        schema = self.schemas.get(class_)
        if not schema:
            schema = copy(self.default_schema)
            self.schemas[class_] = schema
        return schema

    def parser(self, class_: Type) -> Parser:
        schema = self.schema(class_)
        if not schema.parser:
            schema.parser = create_parser(self, schema, self.debug_path, class_)
        return schema.parser

    def serializer(self, class_: Type) -> Serializer:
        schema = self.schema(class_)
        if not schema.serializer:
            schema.serializer = create_serializer(self, schema, self.debug_path, class_)
        return schema.serializer

    def load(self, data: Any, class_: Type):
        return self.parser(class_)(data)

    def dump(self, data: Any, class_: Type = None):
        if class_ is None:
            class_ = type(data)
        return self.serializer(class_)(data)
