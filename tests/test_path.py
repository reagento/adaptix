from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory, NameStyle, Schema
from dataclass_factory.path_utils import NameMapping


@dataclass
class A:
    x: str
    y: str


schema = Schema[A](
    name_mapping={
        "x": ("a", "b", 0),
    },
)

schema_list = Schema[A](
    name_mapping={
        "x": (0, 0),
        "y": (0, 1),
    },
)

schema_tuple = Schema[A](
    name_mapping={
        "x": (0,),
        "y": (1,),
    },
)

path_with_ellipsis = ("sub", ...)
schema_ellipsis = Schema[A](
    name_mapping={
        "x": path_with_ellipsis,
        "y": path_with_ellipsis,
    },
)
schema_auto_ellipsis = Schema[A](
    name_mapping={
        "x": "z",
        ...: path_with_ellipsis,
    },
)
schema_auto_style_ellipsis = Schema[A](
    name_style=NameStyle.upper,
    name_mapping={
        ...: path_with_ellipsis,
    },
)


class TestTyping(TestCase):
    """Some "tests" which are used only to test code with mypy."""

    def test_mapping(self):
        _: NameMapping = {
            "a": "a",
            "b": 1,
            "c": ...,
            "d": ("a",),
            "e": ("b", 1),
            "f": ("a", ..., "b"),
            ...: (1),
        }
        assert _


class Test1(TestCase):
    def test_load(self):
        factory = Factory(
            schemas={
                A: schema,
            },
        )
        data = {
            "a": {"b": ["hello"]},
            "y": "world",
        }
        expected = A("hello", "world")
        self.assertEqual(expected, factory.load(data, A))

    def test_dump(self):
        factory = Factory(
            schemas={
                A: schema,
            },
        )
        expected = {
            "a": {"b": ["hello"]},
            "y": "world",
        }
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))

    def test_dump_ellipsis(self):
        factory = Factory(
            schemas={
                A: schema_ellipsis,
            },
        )
        expected = {
            "sub": {
                "x": "hello",
                "y": "world",
            },
        }
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))
        self.assertEqual(data, factory.load(expected, A))

    def test_dump_auto_style_ellipsis(self):
        factory = Factory(
            schemas={
                A: schema_auto_style_ellipsis,
            },
        )
        expected = {
            "sub": {
                "X": "hello",
                "Y": "world",
            },
        }
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))
        self.assertEqual(data, factory.load(expected, A))

    def test_dump_auto_ellipsis(self):
        factory = Factory(
            schemas={
                A: schema_auto_ellipsis,
            },
        )
        expected = {
            "z": "hello",
            "sub": {
                "y": "world",
            },
        }
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))
        self.assertEqual(data, factory.load(expected, A))

    def test_dump_two(self):
        factory = Factory(
            schemas={
                A: schema,
            },
        )
        expected = {
            "a": {"b": ["hello"]},
            "y": "world",
        }
        expected2 = {
            "a": {"b": ["hello2"]},
            "y": "world2",
        }
        data = A("hello", "world")
        data2 = A("hello2", "world2")
        self.assertEqual(expected, factory.dump(data, A))
        self.assertEqual(expected2, factory.dump(data2, A))

    def test_load_list(self):
        factory = Factory(
            schemas={
                A: schema_list,
            },
        )
        data = [["hello", "world"]]
        expected = A("hello", "world")
        self.assertEqual(expected, factory.load(data, A))

    def test_dump_list(self):
        factory = Factory(
            schemas={
                A: schema_list,
            },
        )
        expected = [["hello", "world"]]
        data = A("hello", "world")
        self.assertEqual(expected, factory.dump(data, A))

    def test_load_plain_list(self):
        factory = Factory(
            schemas={
                A: schema_tuple,
            },
        )
        data = ["hello", "world"]
        expected = A("hello", "world")
        self.assertEqual(expected, factory.load(data, A))

    def test_dump_plain_list(self):
        factory = Factory(
            schemas={
                A: schema_tuple,
            },
        )
        data = ["hello", "world"]
        expected = A("hello", "world")
        self.assertEqual(expected, factory.load(data, A))
