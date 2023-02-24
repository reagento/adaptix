from typing import Literal
from uuid import uuid4

import pytest

from adaptix._internal.provider import LiteralProvider, LoadError
from tests_helpers import TestRetort, parametrize_bool, raises_path


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            LiteralProvider(),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_loader_base(retort, strict_coercion, debug_path):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    ).get_loader(
        Literal["a", "b", 10]
    )

    assert loader("a") == "a"
    assert loader("b") == "b"
    assert loader(10) == 10

    raises_path(
        LoadError(),
        lambda: loader("c")
    )


def rnd():
    return uuid4().hex


def _is_exact_zero(arg):
    return type(arg) == int and arg == 0


def _is_exact_one(arg):
    return type(arg) == int and arg == 1


@parametrize_bool('debug_path')
def test_strict_coercion(retort, debug_path):
    # Literal definition could have very strange behavior
    # due to type cache and 0 == False, 1 == True,
    # so Literal[0, 1] sometimes returns Literal[False, True]
    # and vice versa.
    # We add a random string at the end to suppress caching
    int_loader = retort.replace(
        strict_coercion=True,
        debug_path=debug_path,
    ).get_loader(
        Literal[0, 1, rnd()]  # noqa
    )

    assert _is_exact_zero(int_loader(0))
    assert _is_exact_one(int_loader(1))

    raises_path(
        LoadError(),
        lambda: int_loader(False)
    )
    raises_path(
        LoadError(),
        lambda: int_loader(True)
    )

    bool_loader = retort.replace(
        strict_coercion=True,
        debug_path=debug_path,
    ).get_loader(
        Literal[False, True, rnd()]  # noqa
    )

    assert bool_loader(False) is False
    assert bool_loader(True) is True

    raises_path(
        LoadError(),
        lambda: bool_loader(0)
    )
    raises_path(
        LoadError(),
        lambda: bool_loader(1)
    )
