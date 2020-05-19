from typing import Dict, Optional
from unittest import TestCase

from dataclasses import dataclass

from dataclass_factory import Factory, Schema
from dataclass_factory.schema import Unknown


@dataclass
class Sub:
    b: str


@dataclass
class Data:
    a: str
    unknown: Optional[Dict] = None
    sub: Optional[Sub] = None


@dataclass
class DataAllUnknown:
    sub: Optional[Sub] = None


class DataWithExtras:
    def __init__(self, a: str, **kwargs):
        self.a = a
        self.extras = kwargs


class TestFactory(TestCase):
    def test_skip(self):
        factory = Factory(
            default_schema=Schema(
                unknown=Unknown.SKIP,
            ),
        )
        data = Data("AA")
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, Data))

    def test_store_separate(self):
        factory = Factory(
            default_schema=Schema(
                unknown="unknown",
            ),
        )
        data = Data("AA", {"b": "b"})
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, Data))
        self.assertEqual({"a": "AA", "b": "b", "sub": None}, factory.dump(data))

    def test_store_separate_multiple(self):
        factory = Factory(
            default_schema=Schema(
                unknown=["unknown", "sub"],
            ),
        )
        data = Data("AA", {"b": "b"}, Sub("b"))
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, Data))
        self.assertEqual({"a": "AA", "b": "b"}, factory.dump(data))

    def test_store_separate_parse(self):
        factory = Factory(
            default_schema=Schema(
                unknown=["unknown", "sub"],
            ),
        )
        data = DataAllUnknown(Sub("b"))
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, DataAllUnknown))
        self.assertEqual({"b": "b"}, factory.dump(data))

    def test_forbid(self):
        factory = Factory(
            default_schema=Schema(
                unknown=Unknown.FORBID,
            ),
        )
        serialized = {"a": "AA", "b": "b"}
        with self.assertRaises(ValueError):
            factory.load(serialized, Data)

    def test_include(self):
        factory = Factory(
            default_schema=Schema(
                unknown=Unknown.STORE,
            ),
        )
        serialized = {"a": "AA", "b": "b"}
        data = factory.load(serialized, DataWithExtras)
        self.assertEqual(data.a, "AA")
        self.assertEqual(data.extras, {"b": "b"})
