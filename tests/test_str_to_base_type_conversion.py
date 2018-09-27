#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from decimal import Decimal
from unittest import TestCase

from dataclass_factory import parse


@dataclass
class Foo:
    a: int = 0
    b: float = 0.
    c: bool = False
    e: Decimal = Decimal("0")


class TestStrToBaseTypeConversion(TestCase):

    def test_should_convert_to_int_when_valid_parsing_valid_int(self):
        self.assertEqual(parse({"a": "10"}, Foo), Foo(a=10))
        self.assertEqual(parse({"a": "-120"}, Foo), Foo(a=-120))

    def test_should_raise_when_invalid_int_provided(self):
        self.assertRaises(ValueError, parse, {"a": ""}, Foo)
        self.assertRaises(ValueError, parse, {"a": "10.3"}, Foo)
        self.assertRaises(ValueError, parse, {"a": "-120e"}, Foo)

    def test_should_convert_to_float_when_valid_parsing_valid_float(self):
        self.assertEqual(parse({"b": "10"}, Foo), Foo(b=10.))
        self.assertEqual(parse({"b": "-120"}, Foo), Foo(b=-120.))
        self.assertEqual(parse({"b": "13.6"}, Foo), Foo(b=13.6))
        self.assertEqual(parse({"b": "13e6"}, Foo), Foo(b=13e6))
        self.assertEqual(parse({"b": "0"}, Foo), Foo(b=0))

    def test_should_raise_when_invalid_float_provided(self):
        self.assertRaises(ValueError, parse, {"b": ""}, Foo)
        self.assertRaises(ValueError, parse, {"b": "10.3."}, Foo)
        self.assertRaises(ValueError, parse, {"b": "-120e"}, Foo)

    def test_should_not_convert_to_bool_when_boolean_field_parsing(self):
        self.assertEqual(parse({}, Foo), Foo(c=False))
        self.assertEqual(parse({"c": "True"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": "False"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": "true"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": "1"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": "0"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": ""}, Foo), Foo(c=False))

    def test_should_convert_to_decimal_when_valid_parsing_valid_decimal(self):
        self.assertEqual(parse({"e": "10"}, Foo), Foo(e=Decimal("10")))
        self.assertEqual(parse({"e": "-120"}, Foo), Foo(e=Decimal("-120")))
        self.assertEqual(parse({"e": "13.6"}, Foo), Foo(e=Decimal("13.6")))
        self.assertEqual(parse({"e": "13e6"}, Foo), Foo(e=Decimal("13e6")))
        self.assertEqual(parse({"e": "0"}, Foo), Foo(e=Decimal("0")))

    def test_should_raise_when_invalid_decimal_provided(self):
        self.assertRaises(ValueError, parse, {"e": ""}, Foo)
        self.assertRaises(ValueError, parse, {"e": "10.3."}, Foo)
        self.assertRaises(ValueError, parse, {"e": "-120e"}, Foo)
