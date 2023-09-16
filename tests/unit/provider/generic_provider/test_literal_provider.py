from typing import Literal
from uuid import uuid4

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix._internal.load_error import LoadError
from adaptix._internal.provider.generic_provider import LiteralProvider


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            LiteralProvider(),
        ]
    )


def test_loader_base(retort, strict_coercion, debug_trail):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal["a", "b", 10]
    )

    assert loader("a") == "a"
    assert loader("b") == "b"
    assert loader(10) == 10

    raises_exc(
        LoadError(),
        lambda: loader("c")
    )


def rnd():
    return uuid4().hex


def _is_exact_zero(arg):
    return type(arg) == int and arg == 0


def _is_exact_one(arg):
    return type(arg) == int and arg == 1


def test_strict_coercion(retort, debug_trail):
    # Literal definition could have very strange behavior
    # due to type cache and 0 == False, 1 == True,
    # so Literal[0, 1] sometimes returns Literal[False, True]
    # and vice versa.
    # We add a random string at the end to suppress caching
    int_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[0, 1, rnd()]
    )

    assert _is_exact_zero(int_loader(0))
    assert _is_exact_one(int_loader(1))

    raises_exc(
        LoadError(),
        lambda: int_loader(False)
    )
    raises_exc(
        LoadError(),
        lambda: int_loader(True)
    )

    bool_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[False, True, rnd()]
    )

    assert bool_loader(False) is False
    assert bool_loader(True) is True

    raises_exc(
        LoadError(),
        lambda: bool_loader(0)
    )
    raises_exc(
        LoadError(),
        lambda: bool_loader(1)
    )
