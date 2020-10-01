from dataclasses import asdict, dataclass
from unittest import TestCase

from dataclass_factory import dict_factory, parse


class Bar:
    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        return self.data == other.data


@dataclass
class Foo:
    a: int
    b: Bar


def bar_factory(data):
    return Bar(data * 10 + 3)


def int_factory(data):
    return len(data)


def bar_serialize(bar: Bar):
    return bar.data - 3 // 10


class TestTypeFactories(TestCase):
    def test_parse(self):
        data = {
            "a": [1, 2, 3],
            "b": 4,
        }
        expected = Foo(a=3, b=Bar(43))
        self.assertEqual(
            parse(data, Foo, type_factories={int: int_factory, Bar: bar_factory}),
            expected,
        )

    def test_serialize(self):
        data = Foo(a=3, b=Bar(43))
        expected = {
            "a": 3,
            "b": 4,
        }
        self.assertTrue(
            asdict(data, dict_factory=dict_factory(type_serializers={Bar: bar_serialize})),
            expected,
        )
