#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Dict, ClassVar, Callable, Any

from dataclass_factory.dict_factory import dict_factory
from .parsers import ParserFactory


def parse(data, cls, trim_trailing_underscore: bool = True, type_factories: Dict[Any, Callable] = None):
    return ParserFactory(
        trim_trailing_underscore=trim_trailing_underscore,
        type_factories=type_factories
    ).get_parser(cls)(data)


__all__ = [
    "parse",
    "dict_factory"
]
