from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Schema, Factory


@dataclass
class A:
    x: str
    y: str


schema = Schema(
    name_mapping={
        "x": ("a", "b", 0),
    }
)


class Test1(TestCase):
    def test_path(self):
        factory = Factory(
            schemas={
                A: schema
            }
        )
        data = {
            "a": {"b": ["hello"]},
            "y": "world"
        }
        expected = A("hello", "world")
        self.assertEqual(expected, factory.load(data, A))
