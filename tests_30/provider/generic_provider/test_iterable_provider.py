import collections
from collections import deque
from typing import Dict, Mapping, List, Iterable

import pytest

from dataclass_factory_30.provider import (
    IterableProvider,
    CoercionLimiter,
    CannotProvide,
    ParserRequest,
    SerializerRequest,
    as_parser,
    as_serializer,
)
from dataclass_factory_30.provider.definitions import TypeParseError, ExcludedTypeParseError
from tests_30.provider.conftest import TestFactory, raises_instance, parametrize_bool


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            IterableProvider(),
            CoercionLimiter(as_parser(str), [str]),
            as_serializer(str, str),  # this serializer differ from a builtin one
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_mapping_providing(factory, strict_coercion, debug_path):
    with pytest.raises(CannotProvide):
        factory.provide(
            ParserRequest(
                type=dict,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(CannotProvide):
        factory.provide(
            ParserRequest(
                type=Dict,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(CannotProvide):
        factory.provide(
            ParserRequest(
                type=Mapping,
                strict_coercion=strict_coercion,
                debug_path=debug_path,
            )
        )

    with pytest.raises(CannotProvide):
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

    raises_instance(
        TypeParseError(Iterable),
        lambda: parser(123)
    )

    if not strict_coercion:
        assert parser({"a": 0, "b": 0, "c": 0}) == ["a", "b", "c"]
        assert parser(collections.OrderedDict({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]
        assert parser(collections.ChainMap({"a": 0, "b": 0, "c": 0})) == ["a", "b", "c"]

    if strict_coercion:
        raises_instance(
            ExcludedTypeParseError(Mapping),
            lambda: parser({"a": 0, "b": 0, "c": 0})
        )

        raises_instance(
            ExcludedTypeParseError(Mapping),
            lambda: parser(collections.ChainMap({"a": 0, "b": 0, "c": 0}))
        )

        if debug_path:
            path1 = deque([0])
            path2 = deque([1])
        else:
            path1 = None
            path2 = None

        raises_instance(
            TypeParseError(str, path=path1),
            lambda: parser([1, 2, 3])
        )

        raises_instance(
            TypeParseError(str, path=path2),
            lambda: parser(["1", 2, 3])
        )


@parametrize_bool('debug_path')
def test_serializing(factory, debug_path):
    list_serializer = factory.provide(
        SerializerRequest(
            type=List[str],
            debug_path=debug_path,
        )
    )

    assert list_serializer(["a", "b"]) == ["a", "b"]
    assert list_serializer([1, 2]) == ["1", "2"]

    iterable_serializer = factory.provide(
        SerializerRequest(
            type=Iterable[str],
            debug_path=debug_path,
        )
    )

    assert iterable_serializer(["a", "b"]) == ("a", "b")
    assert iterable_serializer(("a", "b")) == ("a", "b")
    assert iterable_serializer([1, 2]) == ("1", "2")
    assert iterable_serializer({"a": 0, "b": 0}) == ("a", "b")
