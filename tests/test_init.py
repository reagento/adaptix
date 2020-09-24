from enum import Enum
from unittest import TestCase

from dataclass_factory import Factory


class E(Enum):
    one = 1
    hello = "hello"


class MyClass:
    def __init__(self, x: int, y: E, z):
        self.x = x
        self.y = y
        self.z = z

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z


class TestInit(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    def test_load(self):
        data = {
            "x": 1,
            "y": "hello",
            "z": "z"
        }
        expected = MyClass(1, E.hello, "z")
        self.assertEqual(self.factory.load(data, MyClass), expected)

    def test_dump(self):
        expected = {
            "x": 1,
            "y": "hello",
            "z": "z"
        }
        data = MyClass(1, E.hello, "z")
        self.assertEqual(self.factory.dump(data, MyClass), expected)
