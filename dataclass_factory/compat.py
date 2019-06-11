#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Dict, Any, Callable, Type

from .common import Parser
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
        """
        :param trim_trailing_underscore: allows to trim trailing underscore in dataclass field names when looking them in corresponding dictionary.
            For example field `id_` can be stored is `id`
        :param debug_path: allows to see path to an element, that cannot be parsed in raised Exception.
            This causes some performance decrease
        :param type_factories: dictionary with type as a key and functions that can be used to create instances of corresponding types as value
        :param name_styles: style for names in dict which are parsed as dataclass (snake_case, CamelCase, etc.)
        """
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

        default_schema = Schema(
            trim_trailing_underscore=trim_trailing_underscore,
        )
        self.factory = Factory(
            default_schema=default_schema,
            debug_path=debug_path,
            schemas=schemas
        )

    def get_parser(self, cls: Type) -> Parser:
        return self.factory.parser(cls)


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
