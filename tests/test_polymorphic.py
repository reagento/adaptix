import unittest
from typing import Union

from dataclasses import dataclass

from dataclass_factory import Factory, Schema
from dataclass_factory.schema_helpers import type_checker


@dataclass
class A:
    a: str
    b: int = 0


@dataclass
class B:
    a: str
    b: int = 1


@dataclass
class C:
    a: str
    b: int = 2


Some = Union[A, B, C]


def pre_parse(data):
    return {
        "x": data["x"],
        "a": data["a"] + "*"
    }


class MyTestCase(unittest.TestCase):
    def test_choice(self):
        factory = Factory(schemas={
            A: Schema(pre_parse=type_checker("A", field="x")),
            B: Schema(pre_parse=type_checker("B", field="x")),
            C: Schema(pre_parse=type_checker("C", field="x")),
        })
        self.assertEqual(factory.load({"a": "hello", "x": "A"}, Some), A("hello"))
        self.assertEqual(factory.load({"a": "hello", "x": "B"}, Some), B("hello"))
        self.assertEqual(factory.load({"a": "hello", "x": "C"}, Some), C("hello"))

    def test_nothing(self):
        factory = Factory(schemas={
            A: Schema(pre_parse=type_checker("A", field="x")),
            B: Schema(pre_parse=type_checker("B", field="x")),
            C: Schema(pre_parse=type_checker("C", field="x")),
        })
        self.assertRaises((ValueError, KeyError, TypeError, AttributeError),
                          factory.load, {"a": "hello", "x": "XXX"}, Some)
        self.assertRaises((ValueError, KeyError, TypeError, AttributeError),
                          factory.load, {"a": "hello"}, Some)

    def test_pre_parse(self):
        factory = Factory(schemas={
            A: Schema(pre_parse=type_checker("A", field="x", pre_parse=pre_parse)),
            B: Schema(pre_parse=type_checker("B", field="x", pre_parse=pre_parse)),
            C: Schema(pre_parse=type_checker("C", field="x", pre_parse=pre_parse)),
        })
        self.assertEqual(factory.load({"a": "hello", "x": "B"}, Some), B("hello*"))
