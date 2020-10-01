from enum import Enum
from typing import Any, Callable, Dict, Type
import warnings

from .common import Parser, Serializer
from .factory import Factory
from .naming import NameStyle
from .schema import Schema


def dict_factory(trim_trailing_underscore=True, skip_none=False, skip_internal=False,
                 type_serializers: Dict[type, Callable] = None):
    warnings.warn("this function is deprecated",
                  DeprecationWarning,
                  stacklevel=2)

    def impl(data):
        return {
            (k.rstrip("_") if trim_trailing_underscore else k): _prepare_value(v, type_serializers=type_serializers)
            for k, v in data
            if not (k.startswith("_") and skip_internal) and (v is not None or not skip_none)
        }

    return impl


def _prepare_value(value, type_serializers: Dict[type, Callable] = None):
    if type_serializers and (type(value)) in type_serializers:
        return type_serializers[type(value)](value)
    if isinstance(value, Enum):
        return value.value
    return value


class ParserFactory:
    def __init__(
            self,
            trim_trailing_underscore: bool = True,
            debug_path: bool = False,
            type_factories: Dict[Type, Parser] = None,
            name_styles: Dict[Type, NameStyle] = None,
    ):
        warnings.warn("this class is deprecated",
                      DeprecationWarning,
                      stacklevel=2)

        if type_factories is None:
            type_factories = {}
        if name_styles is None:
            name_styles = {}

        schemas = {}
        for c in (set(type_factories) | set(name_styles)):
            schemas[c] = Schema(
                parser=type_factories.get(c),
                name_style=name_styles.get(c),
            )

        default_schema = Schema[Any](
            trim_trailing_underscore=trim_trailing_underscore,
        )
        self.factory = Factory(
            default_schema=default_schema,
            debug_path=debug_path,
            schemas=schemas,
        )

    def get_parser(self, cls: Type) -> Parser:
        return self.factory.parser(cls)


class SerializerFactory:
    def __init__(self,
                 trim_trailing_underscore: bool = True,
                 debug_path: bool = False,
                 type_serializers: Dict[Type, Serializer] = None,
                 name_styles: Dict[Type, NameStyle] = None,
                 ):
        warnings.warn("this class is deprecated",
                      DeprecationWarning,
                      stacklevel=2)

        if type_serializers is None:
            type_serializers = {}
        if name_styles is None:
            name_styles = {}

        schemas = {}
        for c in (set(type_serializers) | set(name_styles)):
            schemas[c] = Schema(
                serializer=type_serializers.get(c),
                name_style=name_styles.get(c),
            )

        default_schema = Schema[Any](
            trim_trailing_underscore=trim_trailing_underscore,
        )
        self.factory = Factory(
            default_schema=default_schema,
            debug_path=debug_path,
            schemas=schemas,
        )

    def get_serializer(self, cls: Type) -> Parser:
        return self.factory.serializer(cls)


def parse(
        data,
        cls,
        trim_trailing_underscore: bool = True,
        type_factories: Dict[Any, Callable] = None,
):
    warnings.warn("this function is deprecated",
                  DeprecationWarning,
                  stacklevel=2)

    return ParserFactory(
        trim_trailing_underscore=trim_trailing_underscore,
        debug_path=True,
        type_factories=type_factories,
    ).get_parser(cls)(data)
