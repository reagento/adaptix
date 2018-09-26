#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from enum import Enum
from unittest import TestCase

from dataclass_factory import parse


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
            parse({"a": "20x", "b": 20}, Foo)
            self.assertTrue(False, "ValueError exception expected")
        except ValueError as exc:
            self.assertEqual(("Unknown type `<class 'int'>` or invalid data: '20x'", 'a'), exc.args)

    def test_should_provide_failed_key_hierarchy_when_invalid_nested_data_parsed(self):
        try:
            parse({"d": {"a": "20x", "b": 20}, "e": 1}, Bar)
            self.assertTrue(False, "ValueError exception expected")
        except ValueError as exc:
            self.assertEqual(("Unknown type `<class 'int'>` or invalid data: '20x'", 'a', 'd'), exc.args)
