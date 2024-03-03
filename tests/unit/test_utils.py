import pickle
from copy import copy, deepcopy

import pytest

from adaptix._internal.utils import SingletonMeta, get_prefix_groups


class SomeSingleton(metaclass=SingletonMeta):
    pass


def test_singleton_simple():
    instance1 = SomeSingleton()
    instance2 = SomeSingleton()

    assert instance1 is instance2
    assert instance1 == instance2


def test_singleton_repr():
    class MyReprSingleton(metaclass=SingletonMeta):
        def __repr__(self):
            return "<CustomSingletonRepr>"

    assert repr(SomeSingleton()) == "SomeSingleton()"
    assert repr(MyReprSingleton()) == "<CustomSingletonRepr>"


def test_singleton_hash():
    hash(SomeSingleton())


def test_singleton_copy():
    assert copy(SomeSingleton()) is SomeSingleton()
    assert deepcopy(SomeSingleton()) is SomeSingleton()

    assert pickle.loads(pickle.dumps(SomeSingleton())) is SomeSingleton()  # noqa: S301


def test_singleton_new():
    assert SomeSingleton.__new__(SomeSingleton) is SomeSingleton()


@pytest.mark.parametrize(
    ["values", "result"],
    [
        (
            [],
            [],
        ),
        (
            ["a"],
            [],
        ),
        (
            ["a", "b"],
            [],
        ),
        (
            ["a", "b", "c"],
            [],
        ),
        (
            ["a", "ab", "ac"],
            [("a", ["ab", "ac"])],
        ),
        (
            ["a", "ab", "ac", "foo"],
            [("a", ["ab", "ac"])],
        ),
        (
            ["a", "ab", "ac", "foo", "bar", "bar1"],
            [("a", ["ab", "ac"]), ("bar", ["bar1"])],
        ),
    ],
)
def test_get_prefix_groups(values, result):
    assert get_prefix_groups(values) == result
