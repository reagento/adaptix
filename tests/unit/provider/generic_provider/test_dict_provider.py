import collections.abc
from typing import Dict

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix import DebugTrail, dumper, loader
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.load_error import AggregateLoadError
from adaptix._internal.provider.concrete_provider import STR_LOADER_PROVIDER
from adaptix._internal.provider.generic_provider import DictProvider
from adaptix._internal.struct_trail import ItemKey, append_trail, extend_trail
from adaptix.load_error import TypeLoadError


def string_dumper(data):
    if isinstance(data, str):
        return data
    raise TypeError


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            DictProvider(),
            STR_LOADER_PROVIDER,
            dumper(str, string_dumper),
        ]
    )


class MyMapping:
    def __init__(self, dct):
        self.dct = dct

    def __getattr__(self, item):
        return getattr(self.dct, item)


def test_loading(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Dict[str, str],
    )

    assert loader_({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}
    assert loader_(MyMapping({'a': 'b', 'c': 'd'})) == {'a': 'b', 'c': 'd'}

    raises_exc(
        TypeLoadError(collections.abc.Mapping, 123),
        lambda: loader_(123),
    )

    raises_exc(
        TypeLoadError(collections.abc.Mapping, ['a', 'b', 'c']),
        lambda: loader_(['a', 'b', 'c']),
    )

    if strict_coercion:
        if debug_trail == DebugTrail.DISABLE:
            raises_exc(
                TypeLoadError(str, 0),
                lambda: loader_({'a': 'b', 'c': 0}),
            )
            raises_exc(
                TypeLoadError(str, 0),
                lambda: loader_({'a': 'b', 0: 'd'}),
            )
        elif debug_trail == DebugTrail.FIRST:
            raises_exc(
                extend_trail(TypeLoadError(str, 0), ['c']),
                lambda: loader_({'a': 'b', 'c': 0}),
            )
            raises_exc(
                extend_trail(TypeLoadError(str, 0), [ItemKey(0)]),
                lambda: loader_({'a': 'b', 0: 'd'}),
            )
        elif debug_trail == DebugTrail.ALL:
            raises_exc(
                AggregateLoadError(
                    "while loading <class 'dict'>",
                    [append_trail(TypeLoadError(str, 0), 'c')]
                ),
                lambda: loader_({'a': 'b', 'c': 0}),
            )
            raises_exc(
                AggregateLoadError(
                    "while loading <class 'dict'>",
                    [append_trail(TypeLoadError(str, 0), ItemKey(0))]
                ),
                lambda: loader_({'a': 'b', 0: 'd'}),
            )


def bad_string_loader(data):
    if isinstance(data, str):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def test_loader_unexpected_error(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).extend(
        recipe=[
            loader(str, bad_string_loader),
        ]
    ).get_loader(
        Dict[str, str],
    )

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: loader_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            TypeError(),
            lambda: loader_({'a': 'b', 0: 'd'}),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            extend_trail(TypeError(), ['c']),
            lambda: loader_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            extend_trail(TypeError(), [ItemKey(0)]),
            lambda: loader_({'a': 'b', 0: 'd'}),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while loading <class 'dict'>",
                [append_trail(TypeError(), 'c')]
            ),
            lambda: loader_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            CompatExceptionGroup(
                "while loading <class 'dict'>",
                [append_trail(TypeError(), ItemKey(0))]
            ),
            lambda: loader_({'a': 'b', 0: 'd'}),
        )


def test_dumping(retort, debug_trail):
    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Dict[str, str],
    )

    assert dumper_({'a': 'b', 'c': 'd'}) == {'a': 'b', 'c': 'd'}

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            TypeError(),
            lambda: dumper_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            TypeError(),
            lambda: dumper_({'a': 'b', 0: 'd'}),
        )
    elif debug_trail == DebugTrail.FIRST:
        raises_exc(
            extend_trail(TypeError(), ['c']),
            lambda: dumper_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            extend_trail(TypeError(), [ItemKey(0)]),
            lambda: dumper_({'a': 'b', 0: 'd'}),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                "while dumping <class 'dict'>",
                [append_trail(TypeError(), 'c')],
            ),
            lambda: dumper_({'a': 'b', 'c': 0}),
        )
        raises_exc(
            CompatExceptionGroup(
                "while dumping <class 'dict'>",
                [append_trail(TypeError(), ItemKey(0))],
            ),
            lambda: dumper_({'a': 'b', 0: 'd'}),
        )
