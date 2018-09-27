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


class TestBytesToBaseTypeConversion(TestCase):

    def test_should_convert_to_int_when_valid_parsing_valid_int(self):
        self.assertEqual(parse({"a": b"10"}, Foo), Foo(a=10))
        self.assertEqual(parse({"a": b"-120"}, Foo), Foo(a=-120))

    def test_should_raise_when_invalid_int_provided(self):
        self.assertRaises(ValueError, parse, {"a": b""}, Foo)
        self.assertRaises(ValueError, parse, {"a": b"10.3"}, Foo)
        self.assertRaises(ValueError, parse, {"a": b"-120e"}, Foo)

    def test_should_convert_to_float_when_valid_parsing_valid_float(self):
        self.assertEqual(parse({"b": b"10"}, Foo), Foo(b=10.))
        self.assertEqual(parse({"b": b"-120"}, Foo), Foo(b=-120.))
        self.assertEqual(parse({"b": b"13.6"}, Foo), Foo(b=13.6))
        self.assertEqual(parse({"b": b"13e6"}, Foo), Foo(b=13e6))
        self.assertEqual(parse({"b": b"0"}, Foo), Foo(b=0))

    def test_should_raise_when_invalid_float_provided(self):
        self.assertRaises(ValueError, parse, {"b": b""}, Foo)
        self.assertRaises(ValueError, parse, {"b": b"10.3."}, Foo)
        self.assertRaises(ValueError, parse, {"b": b"-120e"}, Foo)

    def test_should_not_convert_to_bool_when_boolean_field_parsing(self):
        self.assertEqual(parse({}, Foo), Foo(c=False))
        self.assertEqual(parse({"c": b"True"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": b"False"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": b"true"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": b"1"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": b"0"}, Foo), Foo(c=True))
        self.assertEqual(parse({"c": b""}, Foo), Foo(c=False))

    def test_should_raise_when_bytes_representation_of_decimal_provided(self):
        self.assertRaises(ValueError, parse, {"e": b"10"}, Foo)
        self.assertRaises(ValueError, parse, {"e": b""}, Foo)
        self.assertRaises(ValueError, parse, {"e": b"10.3."}, Foo)
        self.assertRaises(ValueError, parse, {"e": b"-120e"}, Foo)
