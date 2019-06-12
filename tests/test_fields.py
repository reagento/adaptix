from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory, Schema


@dataclass
class Data:
    a: str = ""
    b: str = ""
    c: str = ""
    _d: str = ""


class TestFactory(TestCase):
    def test_only(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    only=("b",)
                ),
            }
        )
        data = Data("AA", "BB", "CC")
        serial = {"b": "BB"}
        self.assertEqual(factory.dump(data), serial)
        data2 = Data(b="BB")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_exclude(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    exclude=("b",)
                ),
            }
        )
        data = Data("AA", "BB", "CC")
        serial = {"a": "AA", "c": "CC"}
        self.assertEqual(factory.dump(data), serial)
        data2 = Data(a="AA", c="CC")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_mapping(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    name_mapping={"b": "d"}
                ),
            }
        )
        data = Data("AA", "BB", "CC")
        serial = {"a": "AA", "d": "BB", "c": "CC"}
        self.assertEqual(factory.dump(data), serial)
        self.assertEqual(factory.load(serial, Data), data)

    def test_only_mapped(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    name_mapping={"b": "d"},
                    only_mapped=True,
                ),
            }
        )
        data = Data("AA", "BB", "CC")
        serial = {"d": "BB"}
        self.assertEqual(factory.dump(data), serial)
        data2 = Data(b="BB")
        self.assertEqual(factory.load(serial, Data), data2)

    def test_skip_internal(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    skip_internal=True
                ),
            }
        )
        data = Data("AA", "BB", "CC", "DD")
        serial = {"a": "AA", "c": "CC", "b": "BB"}
        self.assertEqual(factory.dump(data), serial)
        data2 = Data("AA", "BB", "CC")
        self.assertEqual(factory.load(serial, Data), data2)
