import collections
import collections.abc
from collections import deque
from collections.abc import Iterable, Mapping
from typing import (
    AbstractSet,
    Collection,
    Deque,
    Dict,
    FrozenSet,
    List,
    MutableSequence,
    MutableSet,
    Reversible,
    Sequence,
    Set,
    Tuple,
)

import pytest
from tests_helpers import raises_exc, with_trail

from adaptix import AdornedRetort, DebugTrail, ProviderNotFoundError, Retort, dumper, loader
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.morphing.iterable_provider import IterableProvider
from adaptix._internal.morphing.load_error import AggregateLoadError
from adaptix.load_error import ExcludedTypeLoadError, TypeLoadError


def string_dumper(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def retort():
    return Retort(
        recipe=[
            dumper(str, string_dumper),
        ],
    )


@pytest.mark.parametrize("mapping_type", [dict, Dict, Mapping, collections.Counter])
def test_mapping_providing(strict_coercion, debug_trail, mapping_type):
    retort = AdornedRetort(
        recipe=[
            IterableProvider(),
        ],
    ).replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )

    with pytest.raises(ProviderNotFoundError):
        retort.get_loader(mapping_type)


def test_loading(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(List[str])

    assert loader_(["a", "b", "c"]) == ["a", "b", "c"]
    assert loader_(("a", "b", "c")) == ["a", "b", "c"]
    assert loader_(deque(["a", "b", "c"])) == ["a", "b", "c"]

    raises_exc(
        TypeLoadError(Iterable, 123),
        lambda: loader_(123),
    )

    if not strict_coercion:
        assert loader_({"a": 0, "b": 0, "c": 0}) == ["a", "b", "c"]
        assert loader_(collections.OrderedDict({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert loader_(collections.ChainMap({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert loader_("abc") == ["a", "b", "c"]

    if strict_coercion:
        raises_exc(
            ExcludedTypeLoadError(Iterable, Mapping, {"a": 0, "b": 0, "c": 0}),
            lambda: loader_({"a": 0, "b": 0, "c": 0}),
        )
        raises_exc(
            ExcludedTypeLoadError(Iterable, Mapping, {"a": 0, "b": 0, "c": 0}),
            lambda: loader_(collections.ChainMap({"a": 0, "b": 0, "c": 0})),
        )
        raises_exc(
            ExcludedTypeLoadError(Iterable, str, "abc"),
            lambda: loader_("abc"),
        )
        if debug_trail == DebugTrail.ALL:
            raises_exc(
                AggregateLoadError(
                    "while loading iterable <class 'list'>",
                    [
                        with_trail(TypeLoadError(str, 1), [0]),
                        with_trail(TypeLoadError(str, 2), [1]),
                        with_trail(TypeLoadError(str, 3), [2]),
                    ],
                ),
                lambda: loader_([1, 2, 3]),
            )
            raises_exc(
                AggregateLoadError(
                    "while loading iterable <class 'list'>",
                    [
                        with_trail(TypeLoadError(str, 2), [1]),
                        with_trail(TypeLoadError(str, 3), [2]),
                    ],
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
                    [] if debug_trail == DebugTrail.DISABLE else [1],
                ),
                lambda: loader_(["1", 2, 3]),
            )


def bad_string_loader(data):
    if isinstance(data, str):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def test_loading_unexpected_error(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).extend(
        recipe=[
            loader(str, bad_string_loader),
        ],
    ).get_loader(List[str])

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: loader_(["1", 2, 3]),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            with_trail(TypeError(), [1]),
            lambda: loader_(["1", 2, 3]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while loading iterable <class 'list'>",
                [
                    with_trail(TypeError(), [1]),
                    with_trail(TypeError(), [2]),
                ],
            ),
            lambda: loader_(["1", 2, 3]),
        )


@pytest.mark.parametrize(
    ["tp", "factory"],
    [
        (Deque[str], deque),
        (Set[str], set),
        (FrozenSet[str], frozenset),
        (Tuple[str, ...], tuple),
    ],
)
def test_specific_type_loading(retort, tp, factory):
    loaded = retort.load(["a", "b", "c"], tp)
    assert loaded == factory(["a", "b", "c"])


@pytest.mark.parametrize(
    ["tp", "factory", "compare_tuple"],
    [
        (Deque[str], deque, True),
        (Set[str], set, False),
        (FrozenSet[str], frozenset, False),
        (Tuple[str, ...], tuple, True),
    ],
)
def test_specific_type_dumping(retort, tp, factory, compare_tuple):
    dumped = retort.dump(factory(["a", "b", "c"]), tp)
    if compare_tuple:
        assert dumped == ("a", "b", "c")
    assert factory(dumped) == factory(["a", "b", "c"])


def test_abc_impl(retort, strict_coercion, debug_trail):
    retort = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )

    for tp in [Iterable, Reversible, Collection, Sequence]:
        loader_ = retort.get_loader(tp[str])
        assert loader_(["a", "b", "c"]) == ("a", "b", "c")

    for tp in [MutableSequence, List]:
        loader_ = retort.get_loader(tp[str])
        assert loader_(["a", "b", "c"]) == ["a", "b", "c"]

    for tp in [AbstractSet, FrozenSet]:
        loader_ = retort.get_loader(tp[str])

        assert loader_(["a", "b", "c"]) == frozenset(["a", "b", "c"])

    for tp in [MutableSet, Set]:
        loader_ = retort.get_loader(tp[str])
        assert loader_(["a", "b", "c"]) == {"a", "b", "c"}


def test_dumping(retort, debug_trail):
    retort = retort.replace(
        debug_trail=debug_trail,
    )
    list_dumper = retort.get_dumper(List[str])
    assert list_dumper(["a", "b"]) == ["a", "b"]
    assert list_dumper({"a": 1, "b": 2}) == ["a", "b"]

    iterable_dumper = retort.get_dumper(Iterable[str])
    assert iterable_dumper(["a", "b"]) == ("a", "b")
    assert iterable_dumper(("a", "b")) == ("a", "b")
    assert iterable_dumper(["1", "2"]) == ("1", "2")
    assert iterable_dumper({"a": 0, "b": 0}) == ("a", "b")

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: iterable_dumper([10, "20"]),
        )
        raises_exc(
            TypeError(),
            lambda: iterable_dumper(["10", 20]),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            with_trail(TypeError(), [0]),
            lambda: iterable_dumper([10, "20"]),
        )
        raises_exc(
            with_trail(TypeError(), [1]),
            lambda: iterable_dumper(["10", 20]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while dumping iterable <class 'collections.abc.Iterable'>",
                [with_trail(TypeError(), [0])],
            ),
            lambda: iterable_dumper([10, "20"]),
        )
        raises_exc(
            CompatExceptionGroup(
                "while dumping iterable <class 'collections.abc.Iterable'>",
                [with_trail(TypeError(), [1])],
            ),
            lambda: iterable_dumper(["10", 20]),
        )
