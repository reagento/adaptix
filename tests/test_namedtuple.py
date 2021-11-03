import sys
import unittest
from collections import namedtuple
from typing import NamedTuple, Tuple
from unittest import TestCase

from dataclass_factory import Factory, Schema
from dataclass_factory.type_detection import is_namedtuple


class A:
    _fields: Tuple = ()


class TypedNamedTuple(NamedTuple):
    field: str
    other: str = "test"




class Complex(NamedTuple):
    sub: TypedNamedTuple


class TestNamedTupleDetection(TestCase):
    def test_typed(self):
        self.assertTrue(is_namedtuple(TypedNamedTuple))
        self.assertTrue(is_namedtuple(namedtuple("T", ["field"])))
        self.assertFalse(is_namedtuple(A))
        self.assertFalse(is_namedtuple(int))


class TestNamedTuple(TestCase):
    def test_typed(self):
        data = {"field": "hello", "other": "test2"}
        factory = Factory()
        parsed = factory.load(data, TypedNamedTuple)
        self.assertEqual(parsed, TypedNamedTuple("hello", "test2"))
        self.assertEqual(factory.dump(parsed), data)

    def test_simple(self):
        data = {"_0": "hello", "field": "test"}
        factory = Factory(default_schema=Schema(skip_internal=False))
        SimpleNamedTuple = namedtuple("SimpleNamedTuple", ["def", "field"], rename=True)
        parsed = factory.load(data, SimpleNamedTuple)
        self.assertEqual(parsed, SimpleNamedTuple("hello", "test"))
        self.assertEqual(factory.dump(parsed), data)

    def test_default_class(self):
        factory = Factory(default_schema=Schema(skip_internal=False, omit_default=True))
        self.assertEqual(factory.dump(TypedNamedTuple("hello")), {"field": "hello"})

    @unittest.skipUnless(sys.version_info[:2] >= (3, 7), "requires Python 3.7+")
    def test_default_functional(self):
        SimpleNamedTuple = namedtuple("SimpleNamedTuple", ["def", "field"],
                                      defaults=["default"], rename=True)
        factory = Factory(default_schema=Schema(skip_internal=False, omit_default=True))
        self.assertEqual(factory.dump(SimpleNamedTuple("hello")), {"_0": "hello"})

    def test_complex(self):
        data = {"sub": {"field": "hello", "other": "test"}}
        factory = Factory()
        parsed = factory.load(data, Complex)
        self.assertEqual(parsed, Complex(TypedNamedTuple("hello")))
        self.assertEqual(factory.dump(parsed), data)
