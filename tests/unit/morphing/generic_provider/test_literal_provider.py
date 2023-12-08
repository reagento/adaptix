from typing import Literal
from uuid import uuid4

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix._internal.load_error import BadVariantError
from adaptix._internal.morphing.generic_provider import LiteralProvider


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
        BadVariantError({'a', 'b', 10}, 'c'),
        lambda: loader("c")
    )


def _is_exact_zero(arg):
    return type(arg) is int and arg == 0


def _is_exact_one(arg):
    return type(arg) is int and arg == 1


def test_strict_coercion(retort, debug_trail):
    # Literal definition could have very strange behavior
    # due to type cache and 0 == False, 1 == True,
    # so Literal[0, 1] sometimes returns Literal[False, True]
    # and vice versa.
    # We add a random string at the end to suppress caching
    rnd_val1 = uuid4().hex
    literal_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[0, 1, rnd_val1]
    )

    assert _is_exact_zero(literal_loader(0))
    assert _is_exact_one(literal_loader(1))

    raises_exc(
        BadVariantError({0, 1, rnd_val1}, False),
        lambda: literal_loader(False)
    )
    raises_exc(
        BadVariantError({0, 1, rnd_val1}, True),
        lambda: literal_loader(True)
    )

    rnd_val2 = uuid4().hex
    bool_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[False, True, rnd_val2]
    )

    assert bool_loader(False) is False
    assert bool_loader(True) is True

    raises_exc(
        BadVariantError({False, True, rnd_val2}, 0),
        lambda: bool_loader(0)
    )
    raises_exc(
        BadVariantError({False, True, rnd_val2}, 1),
        lambda: bool_loader(1)
    )
