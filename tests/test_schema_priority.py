from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory, Schema


@dataclass
class Data:
    a: str = ""
    b: str = ""
    c_: str = ""
    _d: str = ""


class TestFactory(TestCase):
    def test_only_mapping(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    only=("b",),
                    name_mapping={"a": "A"},
                    only_mapped=True,
                ),
            },
        )
        data = Data("AA", "BB", "CC")
        serial = {"b": "BB"}
        self.assertEqual(factory.dump(data), serial)
        serial = {"a": "XXX", "b": "BB"}
        data2 = Data(b="BB")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_only_exclude(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    only=("a", "b"),
                    exclude=("a",),
                ),
            },
        )
        data = Data("AA", "BB", "CC")
        serial = {"b": "BB"}
        self.assertEqual(factory.dump(data), serial)
        serial = {"a": "XXX", "b": "BB"}
        data2 = Data(b="BB")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_trailing_mapping(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    name_mapping={"c_": "c_"},
                    trim_trailing_underscore=True,
                ),
            },
        )
        data = Data("AA", "BB", "CC")
        serial = {"a": "AA", "b": "BB", "c_": "CC"}
        self.assertEqual(factory.dump(data), serial)
        self.assertEqual(factory.load(serial, Data), data)

    def test_internal_only(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    only=("_d",),
                    skip_internal=True,
                ),
            },
        )
        data = Data("AA", "BB", "CC", "DD")
        serial = {"_d": "DD"}
        self.assertEqual(factory.dump(data), serial)
        serial = {"a": "XXX", "_d": "DD"}
        data2 = Data(_d="DD")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_internal_mapping(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    name_mapping={"_d": "_d"},
                    skip_internal=True,
                ),
            },
        )
        data = Data("AA", "BB", "CC", "DD")
        serial = {"a": "AA", "b": "BB", "c": "CC", "_d": "DD"}
        self.assertEqual(factory.dump(data), serial)
        serial = {"a": "XXX", "_d": "DD"}
        data2 = Data(a="XXX", _d="DD")
        self.assertEqual(factory.load(serial, Data), data2)
