import collections.abc
from types import SimpleNamespace
from typing import Dict

import pytest

from dataclass_factory_30.facade import parser, serializer
from dataclass_factory_30.provider import (
    CoercionLimiter,
    DictProvider,
    ParserRequest,
    SerializerRequest,
    TypeParseError,
)
from tests_helpers import TestFactory, parametrize_bool, raises_path


def string_serializer(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            DictProvider(),
            CoercionLimiter(parser(str), [str]),
            serializer(str, string_serializer),
        ]
    )


class MyMapping:
    def __init__(self, dct):
        self.dct = dct

    def __getattr__(self, item):
        return getattr(self.dct, item)


@parametrize_bool('strict_coercion', 'debug_path')
def test_parsing(factory, strict_coercion, debug_path):
    parser = factory.provide(
        ParserRequest(
            type=Dict[str, str],
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}
    assert parser(MyMapping({'a': 'b', 'c': 'd'})) == {'a': 'b', 'c': 'd'}

    raises_path(
        TypeParseError(collections.abc.Mapping),
        lambda: parser(123),
        path=[],
    )

    raises_path(
        TypeParseError(collections.abc.Mapping),
        lambda: parser(['a', 'b', 'c']),
        path=[],
    )

    if strict_coercion:
        raises_path(
            TypeParseError(str),
            lambda: parser({'a': 'b', 'c': 0}),
            path=['c'] if debug_path else [],
        )

        raises_path(
            TypeParseError(str),
            lambda: parser({'a': 'b', 0: 'd'}),
            path=[0] if debug_path else [],
        )


@parametrize_bool('debug_path')
def test_serializing(factory, debug_path):
    serializer = factory.provide(
        SerializerRequest(
            type=Dict[str, str],
            debug_path=debug_path,
        )
    )

    assert serializer({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}

    raises_path(
        TypeError,
        lambda: serializer({'a': 'b', 'c': 0}),
        path=['c'] if debug_path else [],
    )

    raises_path(
        TypeError,
        lambda: serializer({'a': 'b', 0: 'd'}),
        path=[0] if debug_path else [],
    )
