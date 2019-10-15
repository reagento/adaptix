from typing import TypedDict
from unittest import TestCase

from dataclass_factory import Schema, Factory


class A(TypedDict):
    a: str
    b: int



class TestTypedDict(TestCase):
    def test_load(self):
        factory = Factory()
        data = {
            "a": "hello",
            "b": 1
        }
        expected = A(a="hello", b=1)
        self.assertEqual(expected, factory.load(data, A))

    def test_dump(self):
        factory = Factory()
        expected = {
            "a": "hello",
            "b": 1
        }
        data = A(a="hello", b=1)
        self.assertEqual(expected, factory.dump(data, A))
