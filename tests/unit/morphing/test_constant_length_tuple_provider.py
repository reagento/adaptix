import collections
import collections.abc
import typing
from typing import Mapping, Tuple

import pytest
from tests_helpers import TestRetort, raises_exc, requires, with_trail

from adaptix import DebugTrail, NoSuitableProvider, dumper, loader
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.feature_requirement import HAS_UNPACK
from adaptix._internal.morphing.concrete_provider import INT_LOADER_PROVIDER, STR_LOADER_PROVIDER
from adaptix._internal.morphing.constant_length_tuple_provider import ConstantLengthTupleProvider
from adaptix._internal.morphing.load_error import AggregateLoadError
from adaptix.load_error import ExcludedTypeLoadError, ExtraItemsLoadError, NoRequiredItemsLoadError, TypeLoadError


def string_dumper(data):
    if isinstance(data, str):
        return data
    raise TypeError


def int_dumper(data):
    if isinstance(data, int):
        return data
    raise TypeError


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            ConstantLengthTupleProvider(),
            STR_LOADER_PROVIDER,
            dumper(str, string_dumper)
        ]
    )


def test_dynamic_tuple_providing(retort, strict_coercion, debug_trail):
    retort = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail
    )
    with pytest.raises(NoSuitableProvider):
        retort.get_loader(Tuple[str, ...])


def test_loading(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail
    ).get_loader(Tuple[str, str, str])

    assert loader_(["a", "b", "c"]) == ("a", "b", "c")
    assert loader_(("a", "b", "c")) == ("a", "b", "c")

    raises_exc(
        TypeLoadError(tuple, 123),
        lambda: loader_(123)
    )
    if not strict_coercion:
        assert loader_({"a": 0, "b": 0, "c": 0}) == ("a", "b", "c")
        assert loader_(collections.OrderedDict({"a": 0, "b": 0, "c": 0})) == ("a", "b", "c")
        assert loader_(collections.ChainMap({"a": 0, "b": 0, "c": 0})) == ("a", "b", "c")
        assert loader_("abc") == ("a", "b", "c")

    if strict_coercion:
        raises_exc(
            ExcludedTypeLoadError(tuple, Mapping, {"a": 0, "b": 0, "c": 0}),
            lambda: loader_({"a": 0, "b": 0, "c": 0}),
        )
        raises_exc(
            ExcludedTypeLoadError(tuple, Mapping, {"a": 0, "b": 0, "c": 0}),
            lambda: loader_(collections.ChainMap({"a": 0, "b": 0, "c": 0})),
        )
        raises_exc(
            ExcludedTypeLoadError(tuple, str, "abc"),
            lambda: loader_("abc"),
        )
        if debug_trail == DebugTrail.ALL:
            raises_exc(
                AggregateLoadError(
                    "while loading tuple",
                    [
                        with_trail(TypeLoadError(str, 1), [0]),
                        with_trail(TypeLoadError(str, 2), [1]),
                        with_trail(TypeLoadError(str, 3), [2]),
                    ]
                ),
                lambda: loader_([1, 2, 3]),
            )
            raises_exc(
                AggregateLoadError(
                    "while loading tuple",
                    [
                        with_trail(TypeLoadError(str, 2), [1]),
                        with_trail(TypeLoadError(str, 3), [2]),
                    ]
                ),
                lambda: loader_(["1", 2, 3]),
            )
        else:
            raises_exc(
                with_trail(
                    TypeLoadError(str, 1),
                    [] if debug_trail == DebugTrail.DISABLE else [0],
                ),
                lambda: loader_([1, 2, 3]),
            )
            raises_exc(
                with_trail(
                    TypeLoadError(str, 2),
                    [] if debug_trail == DebugTrail.DISABLE else [1]
                ),
                lambda: loader_(["1", 2, 3]),
            )


def bad_int_loader(data):
    if isinstance(data, int):
        return data
    raise TypeError


def test_loading_unexpected_error(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail
    ).extend(
        recipe=[
            loader(int, bad_int_loader)
        ]
    ).get_loader(Tuple[int, int, int])

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: loader_(["1", "2", 3]),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            with_trail(TypeError(), [0]),
            lambda: loader_(["1", "2", 3]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while loading tuple",
                [
                    with_trail(TypeError(), [0]),
                    with_trail(TypeError(), [1]),
                ]
            ),
            lambda: loader_(["1", "2", 3]),
        )


def test_dumping(retort, debug_trail):
    retort = retort.replace(
        debug_trail=debug_trail
    ).extend(
        recipe=[
            dumper(int, int_dumper)
        ]
    )

    first_dumper = retort.get_dumper(Tuple[str, str])
    assert first_dumper(["a", "b"]) == ("a", "b")
    assert first_dumper({'a': 1, 'b': 2}) == ('a', 'b')
    assert first_dumper(["a", "b"]) == ("a", "b")
    assert first_dumper(("a", "b")) == ("a", "b")
    assert first_dumper(['1', '2']) == ("1", "2")
    assert first_dumper({"a": 0, "b": 0}) == ("a", "b")

    second_dumper = retort.get_dumper(Tuple[str, int])
    third_dumper = retort.get_dumper(Tuple[int, str])

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: second_dumper([10, '20']),
        )
        raises_exc(
            TypeError(),
            lambda: third_dumper(['10', 20]),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            with_trail(TypeError(), [0]),
            lambda: second_dumper([10, '20']),
        )
        raises_exc(
            with_trail(TypeError(), [0]),
            lambda: third_dumper(['10', 20]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while dumping tuple",
                [
                    with_trail(TypeError(), [0]),
                    with_trail(TypeError(), [1]),
                ]
            ),
            lambda: second_dumper([10, '20']),
        )
        raises_exc(
            CompatExceptionGroup(
                "while dumping tuple",
                [
                    with_trail(TypeError(), [0]),
                    with_trail(TypeError(), [1]),
                ]
            ),
            lambda: third_dumper(['10', 20]),
        )


def test_loading_not_enough_fields(retort):
    retort = retort.extend(
        recipe=[
            INT_LOADER_PROVIDER,
        ]
    )

    loader_ = retort.get_loader(Tuple[int, int])
    raises_exc(
        ExtraItemsLoadError(2, (1, 2, 3)),
        lambda: loader_([1, 2, 3])
    )
    raises_exc(
        NoRequiredItemsLoadError(2, (1,)),
        lambda: loader_([1])
    )


def test_dumping_not_enough_fields(retort):
    retort = retort.extend(
        recipe=[
            dumper(int, int_dumper)
        ]
    )

    dumper_ = retort.get_dumper(Tuple[int, int])
    raises_exc(
        ExtraItemsLoadError(2, [1, 2, 3]),
        lambda: dumper_([1, 2, 3])
    )
    raises_exc(
        NoRequiredItemsLoadError(2, [1]),
        lambda: dumper_([1])
    )


@requires(HAS_UNPACK)
def test_unpack_loading(retort):
    retort = retort.extend(
        recipe=[
            INT_LOADER_PROVIDER,
        ]
    )
    with pytest.raises(NoSuitableProvider):
        retort.get_loader(Tuple[int, typing.Unpack[Tuple[str, ...]], int])

    loader_ = retort.get_loader(Tuple[int, typing.Unpack[Tuple[str]], int])
    assert loader_([1, "2", 3]) == (1, "2", 3)


@requires(HAS_UNPACK)
def test_unpack_dumping(retort):
    retort = retort.extend(
        recipe=[
            dumper(int, int_dumper)
        ]
    )

    with pytest.raises(NoSuitableProvider):
        retort.get_loader(Tuple[int, typing.Unpack[Tuple[str, ...]], int])

    dumper_ = retort.get_dumper(Tuple[int, typing.Unpack[Tuple[str]], int])
    assert dumper_([1, "2", 3]) == (1, "2", 3)
