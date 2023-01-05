import collections.abc
from typing import Dict

import pytest

from _dataclass_factory.provider import CoercionLimiter, DictProvider, DumperRequest, LoaderRequest, TypeHintLocation
from dataclass_factory import dumper, loader
from dataclass_factory.load_error import TypeLoadError
from tests_helpers import TestRetort, parametrize_bool, raises_path


def string_dumper(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            DictProvider(),
            CoercionLimiter(loader(str, str), [str]),
            dumper(str, string_dumper),
        ]
    )


class MyMapping:
    def __init__(self, dct):
        self.dct = dct

    def __getattr__(self, item):
        return getattr(self.dct, item)


@parametrize_bool('strict_coercion', 'debug_path')
def test_loading(retort, strict_coercion, debug_path):
    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=Dict[str, str]),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}
    assert loader(MyMapping({'a': 'b', 'c': 'd'})) == {'a': 'b', 'c': 'd'}

    raises_path(
        TypeLoadError(collections.abc.Mapping),
        lambda: loader(123),
        path=[],
    )

    raises_path(
        TypeLoadError(collections.abc.Mapping),
        lambda: loader(['a', 'b', 'c']),
        path=[],
    )

    if strict_coercion:
        raises_path(
            TypeLoadError(str),
            lambda: loader({'a': 'b', 'c': 0}),
            path=['c'] if debug_path else [],
        )

        raises_path(
            TypeLoadError(str),
            lambda: loader({'a': 'b', 0: 'd'}),
            path=[0] if debug_path else [],
        )


@parametrize_bool('debug_path')
def test_serializing(retort, debug_path):
    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=Dict[str, str]),
            debug_path=debug_path,
        )
    )

    assert dumper({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}

    raises_path(
        TypeError,
        lambda: dumper({'a': 'b', 'c': 0}),
        path=['c'] if debug_path else [],
    )

    raises_path(
        TypeError,
        lambda: dumper({'a': 'b', 0: 'd'}),
        path=[0] if debug_path else [],
    )
