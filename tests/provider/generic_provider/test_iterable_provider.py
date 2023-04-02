import collections
import collections.abc
from collections import deque
from typing import (
    AbstractSet,
    Collection,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    MutableSequence,
    MutableSet,
    Reversible,
    Sequence,
    Set,
)

import pytest

from adaptix import NoSuitableProvider, dumper
from adaptix._internal.provider import IterableProvider
from adaptix._internal.provider.concrete_provider import STR_LOADER_PROVIDER
from adaptix.load_error import ExcludedTypeLoadError, TypeLoadError
from tests_helpers import TestRetort, parametrize_bool, raises_path


def string_dumper(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            IterableProvider(),
            STR_LOADER_PROVIDER,
            dumper(str, string_dumper),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_mapping_providing(retort, strict_coercion, debug_path):
    retort = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    with pytest.raises(NoSuitableProvider):
        retort.get_loader(dict)

    with pytest.raises(NoSuitableProvider):
        retort.get_loader(Dict)

    with pytest.raises(NoSuitableProvider):
        retort.get_loader(Mapping)

    with pytest.raises(NoSuitableProvider):
        retort.get_loader(collections.Counter)


@parametrize_bool('strict_coercion', 'debug_path')
def test_loading(retort, strict_coercion, debug_path):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    ).get_loader(List[str])

    assert loader(["a", "b", "c"]) == ["a", "b", "c"]
    assert loader(("a", "b", "c")) == ["a", "b", "c"]
    assert loader(deque(["a", "b", "c"])) == ["a", "b", "c"]

    raises_path(
        TypeLoadError(Iterable),
        lambda: loader(123),
        path=[],
    )

    if not strict_coercion:
        assert loader({"a": 0, "b": 0, "c": 0}) == ["a", "b", "c"]
        assert loader(collections.OrderedDict({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert loader(collections.ChainMap({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert loader("abc") == ["a", "b", "c"]

    if strict_coercion:
        raises_path(
            ExcludedTypeLoadError(Mapping),
            lambda: loader({"a": 0, "b": 0, "c": 0}),
            path=[],
        )
        raises_path(
            ExcludedTypeLoadError(Mapping),
            lambda: loader(collections.ChainMap({"a": 0, "b": 0, "c": 0})),
            path=[],
        )
        raises_path(
            ExcludedTypeLoadError(str),
            lambda: loader("abc"),
            path=[],
        )
        raises_path(
            TypeLoadError(str),
            lambda: loader([1, 2, 3]),
            path=[0] if debug_path else [],
        )
        raises_path(
            TypeLoadError(str),
            lambda: loader(["1", 2, 3]),
            path=[1] if debug_path else [],
        )


@parametrize_bool('strict_coercion', 'debug_path')
def test_abc_impl(retort, strict_coercion, debug_path):
    retort = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    for tp in [Iterable, Reversible, Collection, Sequence]:
        loader = retort.get_loader(tp[str])
        assert loader(["a", "b", "c"]) == ("a", "b", "c")

    for tp in [MutableSequence, List]:
        loader = retort.get_loader(tp[str])
        assert loader(["a", "b", "c"]) == ["a", "b", "c"]

    for tp in [AbstractSet, FrozenSet]:
        loader = retort.get_loader(tp[str])

        assert loader(["a", "b", "c"]) == frozenset(["a", "b", "c"])

    for tp in [MutableSet, Set]:
        loader = retort.get_loader(tp[str])
        assert loader(["a", "b", "c"]) == {"a", "b", "c"}


@parametrize_bool('debug_path')
def test_serializing(retort, debug_path):
    retort = retort.replace(
        debug_path=debug_path
    )
    list_dumper = retort.get_dumper(List[str])
    assert list_dumper(["a", "b"]) == ["a", "b"]
    assert list_dumper({'a': 1, 'b': 2}) == ['a', 'b']

    iterable_dumper = retort.get_dumper(Iterable[str])
    assert iterable_dumper(["a", "b"]) == ("a", "b")
    assert iterable_dumper(("a", "b")) == ("a", "b")
    assert iterable_dumper(['1', '2']) == ("1", "2")
    assert iterable_dumper({"a": 0, "b": 0}) == ("a", "b")

    raises_path(
        TypeError,
        lambda: iterable_dumper([10, '20']),
        path=[0] if debug_path else [],
    )

    raises_path(
        TypeError,
        lambda: iterable_dumper(['10', 20]),
        path=[1] if debug_path else [],
    )
