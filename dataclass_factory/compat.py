#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Dict, Any, Callable, Type

from .common import Parser, Serializer
from .factory import Factory
from .naming import NameStyle
from .schema import Schema


class ParserFactory:
    def __init__(
            self,
            trim_trailing_underscore: bool = True,
            debug_path: bool = False,
            type_factories: Dict[Type, Parser] = None,
            name_styles: Dict[Type, NameStyle] = None,
    ):
        if type_factories is None:
            type_factories = {}
        if name_styles is None:
            name_styles = {}

        schemas = {}
        for c in (set(type_factories) | set(name_styles)):
            schemas[c] = Schema(
                parser=type_factories.get(c),
                name_style=name_styles.get(c)
            )

        default_schema = Schema[Any](
            trim_trailing_underscore=trim_trailing_underscore,
        )
        self.factory = Factory(
            default_schema=default_schema,
            debug_path=debug_path,
            schemas=schemas
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
        if type_serializers is None:
            type_serializers = {}
        if name_styles is None:
            name_styles = {}

        schemas = {}
        for c in (set(type_serializers) | set(name_styles)):
            schemas[c] = Schema(
                serializer=type_serializers.get(c),
                name_style=name_styles.get(c)
            )

        default_schema = Schema[Any](
            trim_trailing_underscore=trim_trailing_underscore,
        )
        self.factory = Factory(
            default_schema=default_schema,
            debug_path=debug_path,
            schemas=schemas
        )

    def get_serializer(self, cls: Type) -> Parser:
        return self.factory.serializer(cls)


def parse(
        data,
        cls,
        trim_trailing_underscore: bool = True,
        type_factories: Dict[Any, Callable] = None,
):
    return ParserFactory(
        trim_trailing_underscore=trim_trailing_underscore,
        debug_path=True,
        type_factories=type_factories,
    ).get_parser(cls)(data)
