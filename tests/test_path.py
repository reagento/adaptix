from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Schema, Factory


@dataclass
class A:
    x: str
    y: str


schema = Schema[A](
    name_mapping={
        "x": ("a", "b", 0),
    }
)


class Test1(TestCase):
    def test_load(self):
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

    def test_dump(self):
        factory = Factory(
            schemas={
                A: schema
            }
        )
        expected = {
            "a": {"b": ["hello"]},
            "y": "world"
        }
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))

    def test_dump_two(self):
        factory = Factory(
            schemas={
                A: schema
            }
        )
        expected = {
            "a": {"b": ["hello"]},
            "y": "world"
        }
        expected2 = {
            "a": {"b": ["hello2"]},
            "y": "world2"
        }
        data = A("hello", "world")
        data2 = A("hello2", "world2")
        self.assertEqual(expected, factory.dump(data, A))
        self.assertEqual(expected2, factory.dump(data2, A))
