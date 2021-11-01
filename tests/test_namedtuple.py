from collections import namedtuple
from typing import NamedTuple, Tuple
from unittest import TestCase

from dataclass_factory.type_detection import is_namedtuple


class A:
    _fields: Tuple = ()


class TypedNamedTuple(NamedTuple):
    field: str


SimpleNamedTuple = namedtuple("SimpleNamedTuple", ["field"])


class TestNamedTupleDetection(TestCase):
    def test_typed(self):
        self.assertTrue(is_namedtuple(TypedNamedTuple))
        self.assertTrue(is_namedtuple(SimpleNamedTuple))
        self.assertFalse(is_namedtuple(A))
        self.assertFalse(is_namedtuple(int))
