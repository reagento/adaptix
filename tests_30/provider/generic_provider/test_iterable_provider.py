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

from dataclass_factory_30.facade import parser, serializer
from dataclass_factory_30.factory.operating_factory import NoSuitableProvider
from dataclass_factory_30.provider import CoercionLimiter, IterableProvider, ParserRequest, SerializerRequest
from dataclass_factory_30.provider.definitions import ExcludedTypeParseError, TypeParseError
from tests_helpers import TestFactory, parametrize_bool, raises_path


def string_serializer(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            IterableProvider(),
            CoercionLimiter(parser(str), [str]),
            serializer(str, string_serializer),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_mapping_providing(factory, strict_coercion, debug_path):
    with pytest.raises(NoSuitableProvider):
        factory.provide(
            ParserRequest(
                type=dict,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(NoSuitableProvider):
        factory.provide(
            ParserRequest(
                type=Dict,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(NoSuitableProvider):
        factory.provide(
            ParserRequest(
                type=Mapping,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(NoSuitableProvider):
        factory.provide(
            ParserRequest(
                type=collections.Counter,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )


@parametrize_bool('strict_coercion', 'debug_path')
def test_parsing(factory, strict_coercion, debug_path):
    parser = factory.provide(
        ParserRequest(
            type=List[str],
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser(["a", "b", "c"]) == ["a", "b", "c"]
    assert parser(("a", "b", "c")) == ["a", "b", "c"]
    assert parser(deque(["a", "b", "c"])) == ["a", "b", "c"]

    raises_path(
        TypeParseError(Iterable),
        lambda: parser(123),
        path=[],
    )

    if not strict_coercion:
        assert parser({"a": 0, "b": 0, "c": 0}) == ["a", "b", "c"]
        assert parser(collections.OrderedDict({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert parser(collections.ChainMap({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]

    if strict_coercion:
        raises_path(
            ExcludedTypeParseError(Mapping),
            lambda: parser({"a": 0, "b": 0, "c": 0}),
            path=[],
        )

        raises_path(
            ExcludedTypeParseError(Mapping),
            lambda: parser(collections.ChainMap({"a": 0, "b": 0, "c": 0})),
            path=[],
        )

        raises_path(
            TypeParseError(str),
            lambda: parser([1, 2, 3]),
            path=[0] if debug_path else [],
        )

        raises_path(
            TypeParseError(str),
            lambda: parser(["1", 2, 3]),
            path=[1] if debug_path else [],
        )


@parametrize_bool('strict_coercion', 'debug_path')
def test_abc_impl(factory, strict_coercion, debug_path):
    for tp in [Iterable, Reversible, Collection, Sequence]:
        parser = factory.provide(
            ParserRequest(
                type=tp[str],
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

        assert parser(["a", "b", "c"]) == ("a", "b", "c")

    for tp in [MutableSequence, List]:
        parser = factory.provide(
            ParserRequest(
                type=tp[str],
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

        assert parser(["a", "b", "c"]) == ["a", "b", "c"]

    for tp in [AbstractSet, FrozenSet]:
        parser = factory.provide(
            ParserRequest(
                type=tp[str],
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

        assert parser(["a", "b", "c"]) == frozenset(["a", "b", "c"])

    for tp in [MutableSet, Set]:
        parser = factory.provide(
            ParserRequest(
                type=tp[str],
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

        assert parser(["a", "b", "c"]) == {"a", "b", "c"}


@parametrize_bool('debug_path')
def test_serializing(factory, debug_path):
    list_serializer = factory.provide(
        SerializerRequest(
            type=List[str],
            debug_path=debug_path,
        )
    )

    assert list_serializer(["a", "b"]) == ["a", "b"]
    assert list_serializer({'a': 1, 'b': 2}) == ['a', 'b']

    iterable_serializer = factory.provide(
        SerializerRequest(
            type=Iterable[str],
            debug_path=debug_path,
        )
    )

    assert iterable_serializer(["a", "b"]) == ("a", "b")
    assert iterable_serializer(("a", "b")) == ("a", "b")
    assert iterable_serializer(['1', '2']) == ("1", "2")
    assert iterable_serializer({"a": 0, "b": 0}) == ("a", "b")

    raises_path(
        TypeError,
        lambda: iterable_serializer([10, '20']),
        path=[0] if debug_path else [],
    )

    raises_path(
        TypeError,
        lambda: iterable_serializer(['10', 20]),
        path=[1] if debug_path else [],
    )
