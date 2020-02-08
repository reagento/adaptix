from copy import copy
from typing import List, Dict, Callable, Tuple, Optional, Generic, Union

from .common import Serializer, Parser, T, InnerConverter, ParserGetter, SerializerGetter
from .naming import NameStyle
from .path_utils import Path

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]


class Schema(Generic[T]):
    def __init__(
            self,
            only: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None,
            name_mapping: Optional[Dict[str, Union[str, Path]]] = None,
            only_mapped: Optional[bool] = None,

            name_style: Optional[NameStyle] = None,
            trim_trailing_underscore: Optional[bool] = None,
            skip_internal: Optional[bool] = None,

            serializer: Optional[Serializer[T]] = None,
            get_serializer: Optional[SerializerGetter[T]] = None,

            parser: Optional[Parser[T]] = None,
            get_parser: Optional[ParserGetter[T]] = None,

            pre_parse: Optional[Callable] = None,
            post_parse: Optional[InnerConverter[T]] = None,
            pre_serialize: Optional[InnerConverter[T]] = None,
            post_serialize: Optional[Callable] = None,

            omit_default: Optional[bool] = None,
    ):

        if only is not None or not hasattr(self, "only"):
            self.only = only
        if exclude is not None or not hasattr(self, "exclude"):
            self.exclude = exclude
        if name_mapping is not None or not hasattr(self, "name_mapping"):
            self.name_mapping = name_mapping
        if only_mapped is not None or not hasattr(self, "only_mapped"):
            self.only_mapped = only_mapped

        if name_style is not None or not hasattr(self, "name_style"):
            self.name_style = name_style
        if trim_trailing_underscore is not None or not hasattr(self, "trim_trailing_underscore"):
            self.trim_trailing_underscore = trim_trailing_underscore
        if skip_internal is not None or not hasattr(self, "skip_internal"):
            self.skip_internal = skip_internal

        if serializer is not None or not hasattr(self, "serializer"):
            self.serializer = serializer
        if get_serializer is not None or not hasattr(self, "get_serializer"):
            self.get_serializer = get_serializer

        if parser is not None or not hasattr(self, "parser"):
            self.parser = parser
        if get_parser is not None or not hasattr(self, "get_parser"):
            self.get_parser = get_parser

        if pre_parse is not None or not hasattr(self, "pre_parse"):
            self.pre_parse = pre_parse
        if post_parse is not None or not hasattr(self, "post_parse"):
            self.post_parse = post_parse
        if pre_serialize is not None or not hasattr(self, "pre_serialize"):
            self.pre_serialize = pre_serialize
        if post_serialize is not None or not hasattr(self, "post_serialize"):
            self.post_serialize = post_serialize

        if omit_default is not None or not hasattr(self, "omit_default"):
            self.omit_default = omit_default


SCHEMA_FIELDS = [
    "only",
    "exclude",
    "name_mapping",
    "only_mapped",
    "name_style",
    "trim_trailing_underscore",
    "skip_internal",
    "serializer",
    "get_serializer",
    "parser",
    "get_parser",
    "pre_parse",
    "post_parse",
    "pre_serialize",
    "post_serialize",
]


def merge_schema(schema: Optional[Schema], default: Optional[Schema]) -> Schema:
    if schema is None:
        if default:
            return copy(default)
        return Schema()
    if default is None:
        return copy(schema)
    schema = copy(schema)
    for k in SCHEMA_FIELDS:
        if getattr(schema, k) is None:
            setattr(schema, k, getattr(default, k))
    return schema
