# ruff: noqa: FBT003
from enum import Enum
from typing import Any, Iterable, Literal
from uuid import uuid4

import pytest
from tests_helpers import raises_exc

from adaptix import P, Provider, Retort, dumper, loader
from adaptix._internal.morphing.load_error import BadVariantLoadError


def test_loader_base(strict_coercion, debug_trail):
    retort = Retort()
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal["a", "b", 10],
    )

    assert loader("a") == "a"
    assert loader("b") == "b"
    assert loader(10) == 10

    raises_exc(
        BadVariantLoadError({"a", "b", 10}, "c"),
        lambda: loader("c"),
    )


def _is_exact_zero(arg):
    return type(arg) is int and arg == 0


def _is_exact_one(arg):
    return type(arg) is int and arg == 1


def test_strict_coercion(debug_trail):
    # Literal definition could have very strange behavior
    # due to type cache and 0 == False, 1 == True,
    # so Literal[0, 1] sometimes returns Literal[False, True]
    # and vice versa.
    # We add a random string at the end to suppress caching

    retort = Retort()
    rnd_val1 = uuid4().hex
    literal_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[0, 1, rnd_val1],
    )

    assert _is_exact_zero(literal_loader(0))
    assert _is_exact_one(literal_loader(1))

    raises_exc(
        BadVariantLoadError({0, 1, rnd_val1}, False),
        lambda: literal_loader(False),
    )
    raises_exc(
        BadVariantLoadError({0, 1, rnd_val1}, True),
        lambda: literal_loader(True),
    )

    rnd_val2 = uuid4().hex
    bool_loader = retort.replace(
        strict_coercion=True,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[False, True, rnd_val2],
    )

    assert bool_loader(False) is False
    assert bool_loader(True) is True

    raises_exc(
        BadVariantLoadError({False, True, rnd_val2}, 0),
        lambda: bool_loader(0),
    )
    raises_exc(
        BadVariantLoadError({False, True, rnd_val2}, 1),
        lambda: bool_loader(1),
    )


def test_loader_with_enums(strict_coercion, debug_trail):
    retort = Retort()

    class Enum1(Enum):
        CASE1 = 1
        CASE2 = 2

    class Enum2(Enum):
        CASE1 = 1
        CASE2 = 2

    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal["a", Enum1.CASE1, 5],
    )

    assert loader("a") == "a"
    assert loader(1) == Enum1.CASE1
    assert loader(5) == 5

    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[Enum1.CASE1, Enum2.CASE2, 10],
    )

    assert loader(1) == Enum1.CASE1
    assert loader(2) == Enum2.CASE2
    assert loader(10) == 10

    raises_exc(
        BadVariantLoadError({Enum1.CASE1.value, Enum2.CASE2.value, 10}, 15),
        lambda: loader(15),
    )


@pytest.mark.parametrize(
    ["input_data", "recipe"],
    [
        ("YWJj", []),
        ("abc", [loader(P[bytes], lambda x: x.encode())]),
    ],
)
def test_loader_with_bytes(
    strict_coercion,
    debug_trail,
    input_data: Any,
    recipe: Iterable[Provider],
):
    retort = Retort(
        recipe=recipe,
    )

    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[b"abc"],
    )

    assert loader(input_data) == b"abc"

    raises_exc(
        BadVariantLoadError({b"abc"}, "YWJ"),
        lambda: loader("YWJ"),
    )


def test_loader_with_bytes_and_enums(strict_coercion, debug_trail):
    class Enum1(Enum):
        CASE1 = 1
        CASE2 = 2

    retort = Retort()

    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal[b"abc", Enum1.CASE1],
    )

    assert loader("YWJj") == b"abc"
    assert loader(1) == Enum1.CASE1

    raises_exc(
        BadVariantLoadError({b"abc", Enum1.CASE1.value}, "YWJ"),
        lambda: loader("YWJ"),
    )

    raises_exc(
        BadVariantLoadError({b"abc", Enum1.CASE1.value}, 2),
        lambda: loader(2),
    )


def test_dumper_with_enums(strict_coercion, debug_trail):
    retort = Retort()

    class Enum1(Enum):
        CASE1 = 1
        CASE2 = 2

    class Enum2(Enum):
        CASE1 = 1
        CASE2 = 2

    dumper = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_dumper(
        Literal["a", Enum1.CASE1, 5],
    )

    assert dumper("a") == "a"
    assert dumper(Enum1.CASE1) == 1
    assert dumper(5) == 5

    dumper = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_dumper(
        Literal[Enum1.CASE1, Enum2.CASE2, 10],
    )

    assert dumper(Enum1.CASE1) == 1
    assert dumper(Enum1.CASE2) == 2
    assert dumper(10) == 10

@pytest.mark.parametrize(
    ["expected_data", "recipe"],
    [
        ("YWJj", []),
        ("abc", [dumper(P[bytes], lambda x: x.decode())]),
    ],
)
def test_dumper_with_bytes(strict_coercion, debug_trail, expected_data: Any, recipe: Iterable[Provider]):
    retort = Retort(
        recipe=recipe,
    )

    dumper = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_dumper(
        Literal[b"abc"],
    )

    assert dumper(b"abc") == expected_data


def test_dumper_with_bytes_and_enums(strict_coercion, debug_trail):
    class Enum1(Enum):
        CASE1 = 1
        CASE2 = 2

    retort = Retort()

    dumper = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_dumper(
        Literal[b"abc", Enum1.CASE1],
    )

    assert dumper(b"abc") == "YWJj"
    assert dumper(Enum1.CASE1) == 1
