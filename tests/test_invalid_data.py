#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from enum import Enum
from unittest import TestCase

from dataclass_factory import ParserFactory
from dataclass_factory.exceptions import InvalidFieldError


@dataclass
class Foo:
    a: int
    b: int = field(init=False, default=1)
    c: str = "def_value"


class MyEnum(Enum):
    one = 1
    hello = "hello"


@dataclass
class Bar:
    d: Foo
    e: MyEnum


class TestInvalidData(TestCase):

    def test_should_raise_when_invalid_int_field_provided(self):
        try:
            ParserFactory(debug_path=True).get_parser(Foo)({"a": "20x", "b": 20})
            self.assertTrue(False, "ValueError exception expected")
        except InvalidFieldError as exc:
            self.assertEqual(['a',], exc.field_path)

    def test_should_provide_failed_key_hierarchy_when_invalid_nested_data_parsed(self):
        try:
            ParserFactory(debug_path=True).get_parser(Bar)({"d": {"a": "20x", "b": 20}, "e": 1})
            self.assertTrue(False, "ValueError exception expected")
        except InvalidFieldError as exc:
            self.assertEqual(['a', 'd'], exc.field_path)
