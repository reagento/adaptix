import re
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union

import pytest

from _dataclass_factory.provider import (
    DumperRequest,
    LiteralProvider,
    LoaderRequest,
    LoadError,
    TypeHintLocation,
    TypeLoadError,
    UnionLoadError,
    UnionProvider,
)
from dataclass_factory import dumper, loader
from tests_helpers import TestRetort, full_match_regex_str, parametrize_bool, raises_path


@dataclass
class Book:
    price: int
    author: Union[str, List[str]]


def make_loader(tp: type):
    def tp_loader(data):
        if isinstance(data, tp):
            return data
        raise TypeLoadError(tp)

    return loader(tp, tp_loader)


def make_dumper(tp: type):
    def tp_dumper(data):
        if isinstance(data, tp):
            return data
        raise TypeError(type(data))

    return dumper(tp, tp_dumper)


@pytest.fixture
def retort():
    return TestRetort(
        recipe=[
            UnionProvider(),
            make_loader(str),
            make_loader(int),
            make_dumper(str),
            make_dumper(int),
            make_dumper(type(None)),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_loading(retort, strict_coercion, debug_path):
    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=Union[int, str]),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader(1) == 1
    assert loader('a') == 'a'

    if debug_path:
        raises_path(
            UnionLoadError,
            lambda: loader([]),
            path=[],
            match=full_match_regex_str(
                "[TypeLoadError(expected_type=<class 'int'>), TypeLoadError(expected_type=<class 'str'>)]"
            ),
        )
    else:
        raises_path(
            LoadError,
            lambda: loader([]),
            path=[],
            match='',
        )


@parametrize_bool('debug_path')
def test_serializing(retort, debug_path):
    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=Union[int, str]),
            debug_path=debug_path,
        )
    )

    assert dumper(1) == 1
    assert dumper('a') == 'a'

    raises_path(
        KeyError,
        lambda: dumper([]),
        path=[],
        match=full_match_regex_str("<class 'list'>"),
    )


@parametrize_bool('debug_path')
def test_opt_serializing(retort, debug_path):
    opt_dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=Optional[str]),
            debug_path=debug_path,
        )
    )

    assert opt_dumper('a') == 'a'
    assert opt_dumper(None) is None

    raises_path(
        TypeError,
        lambda: opt_dumper([]),
        path=[],
        match=full_match_regex_str("<class 'list'>"),
    )


@parametrize_bool('debug_path')
def test_bad_opt_serializing(retort, debug_path):
    raises_path(
        ValueError,
        lambda: retort.provide(
            DumperRequest(
                loc=TypeHintLocation(type=Union[int, Callable[[int], str]]),
                debug_path=debug_path,
            )
        ),
        path=[],
        match=full_match_regex_str(
            "Can not create dumper for typing.Union[int, typing.Callable[[int], str]]."
            " All cases of union must be class, but found [typing.Callable[[int], str]]"
        ),
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_literal(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            LiteralProvider(),
            UnionProvider(),
            make_loader(type(None)),
            make_dumper(type(None)),
        ]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=Literal['a', None]),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader('a') == 'a'
    assert loader(None) is None

    if debug_path:
        raises_path(
            UnionLoadError([TypeLoadError(type(None)), LoadError()]),
            lambda: loader('b'),
            path=[],
        )
    else:
        raises_path(
            LoadError(),
            lambda: loader('b'),
            path=[],
        )

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=Literal['a', None]),
            debug_path=debug_path,
        )
    )

    assert dumper('a') == 'a'
    assert dumper(None) is None
    assert dumper('b') == 'b'
