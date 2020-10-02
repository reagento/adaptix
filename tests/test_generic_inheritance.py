from dataclasses import dataclass
from typing import Generic, TypeVar
from unittest import TestCase

from dataclass_factory import Factory

T = TypeVar("T")
V = TypeVar("V")


@dataclass
class Foo(Generic[T]):
    f1: T


@dataclass
class Bar(Generic[T, V]):
    b1: T
    b2: V


@dataclass
class Baz(Bar[int, V], Foo[V], Generic[V]):
    pass


class TestGenericInheritance(TestCase):
    def test_inh(self):
        factory = Factory(debug_path=True)
        with self.assertRaises(ValueError):
            factory.load({"f1": 1, "b1": 2, "b2": 3}, Baz[str])
        with self.assertRaises(ValueError):
            factory.load({"f1": "1", "b1": "qwe", "b2": "3"}, Baz[str])
        res = factory.load({"f1": "1", "b1": 2, "b2": "3"}, Baz[str])
        self.assertEqual(res, Baz(f1="1", b1=2, b2="3"))
