from typing import Dict, Optional
from unittest import TestCase

from dataclasses import dataclass

from dataclass_factory import Factory, Schema, Unknown


@dataclass
class Data:
    a: str
    unknown: Optional[Dict] = None


class TestFactory(TestCase):
    def test_skip(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    unknown=Unknown.SKIP,
                ),
            }
        )
        data = Data("AA")
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, Data))

    def test_include(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    unknown="unknown",
                ),
            }
        )
        data = Data("AA", {"b": "b"})
        serialized = {"a": "AA", "b": "b"}
        self.assertEqual(data, factory.load(serialized, Data))

    def test_forbid(self):
        factory = Factory(
            schemas={
                Data: Schema(
                    unknown=Unknown.FORBID,
                ),
            }
        )
        serialized = {"a": "AA", "b": "b"}
        with self.assertRaises(ValueError):
            factory.load(serialized, Data)
