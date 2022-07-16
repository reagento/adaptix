import collections
from collections import deque
from typing import Dict, Iterable, List, Mapping

import pytest

from dataclass_factory_30.facade import parser, serializer
from dataclass_factory_30.factory.operating_factory import NoSuitableProvider
from dataclass_factory_30.provider import CoercionLimiter, IterableProvider, ParserRequest, SerializerRequest
from dataclass_factory_30.provider.definitions import ExcludedTypeParseError, TypeParseError
from tests_30.provider.conftest import TestFactory, parametrize_bool, raises_instance


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            IterableProvider(),
            CoercionLimiter(parser(str), [str]),
            serializer(str, str),  # this serializer differ from a builtin one
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
            path1 = [0]
            path2 = [1]
        else:
            path1 = []
            path2 = []

        raises_instance(
            TypeParseError(str),
            lambda: parser([1, 2, 3]),
            path=path1,
        )

        raises_instance(
            TypeParseError(str),
            lambda: parser(["1", 2, 3]),
            path=path2,
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
