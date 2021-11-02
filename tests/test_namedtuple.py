from collections import namedtuple
from typing import NamedTuple, Tuple
from unittest import TestCase

from dataclass_factory import Factory
from dataclass_factory.type_detection import is_namedtuple


class A:
    _fields: Tuple = ()


class TypedNamedTuple(NamedTuple):
    field: str


SimpleNamedTuple = namedtuple("SimpleNamedTuple", ["field"])


class Complex(NamedTuple):
    sub: TypedNamedTuple


class TestNamedTupleDetection(TestCase):
    def test_typed(self):
        self.assertTrue(is_namedtuple(TypedNamedTuple))
        self.assertTrue(is_namedtuple(SimpleNamedTuple))
        self.assertFalse(is_namedtuple(A))
        self.assertFalse(is_namedtuple(int))


class TestNamedTuple(TestCase):
    def test_typed(self):
        data = {"field": "hello"}
        factory = Factory()
        parsed = factory.load(data, TypedNamedTuple)
        self.assertEqual(parsed, TypedNamedTuple("hello"))
        self.assertEqual(factory.dump(parsed), data)

    def test_simple(self):
        data = {"field": "hello"}
        factory = Factory()
        parsed = factory.load(data, SimpleNamedTuple)
        self.assertEqual(parsed, SimpleNamedTuple("hello"))
        self.assertEqual(factory.dump(parsed), data)

    def test_complex(self):
        data = {"sub": {"field": "hello"}}
        factory = Factory()
        parsed = factory.load(data, Complex)
        self.assertEqual(parsed, Complex(TypedNamedTuple("hello")))
        self.assertEqual(factory.dump(parsed), data)
