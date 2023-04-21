from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union

import pytest

from adaptix import Retort, dumper, loader
from adaptix._internal.provider import LiteralProvider, LoadError, TypeLoadError, UnionLoadError, UnionProvider
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
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    ).get_loader(
        Union[int, str],
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
    dumper = retort.replace(
        debug_path=debug_path,
    ).get_dumper(
        Union[int, str]
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
def test_serializing_subclass(retort, debug_path):
    @dataclass
    class Parent:
        foo: int

    @dataclass
    class Child(Parent):
        bar: int

    dumper = Retort(
        debug_path=debug_path,
    ).get_dumper(
        Union[Parent, str]
    )

    assert dumper(Parent(foo=1)) == {'foo': 1}
    assert dumper(Child(foo=1, bar=2)) == {'foo': 1}
    assert dumper('a') == 'a'

    raises_path(
        KeyError,
        lambda: dumper([]),
        path=[],
        match=full_match_regex_str("<class 'list'>"),
    )



@parametrize_bool('debug_path')
def test_opt_serializing(retort, debug_path):
    opt_dumper = retort.replace(
        debug_path=debug_path,
    ).get_dumper(
        Optional[str],
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
        exc=ValueError,
        func=lambda: retort.replace(
            debug_path=debug_path,
        ).get_dumper(
            Union[int, Callable[[int], str]],
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

    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    ).get_loader(
        Literal['a', None],
    )

    assert loader('a') == 'a'
    assert loader(None) is None

    if debug_path:
        raises_path(
            UnionLoadError([TypeLoadError(None), LoadError()]),
            lambda: loader('b'),
            path=[],
        )
    else:
        raises_path(
            LoadError(),
            lambda: loader('b'),
            path=[],
        )

    dumper = retort.replace(
        debug_path=debug_path,
    ).get_dumper(
        Literal['a', None],
    )

    assert dumper('a') == 'a'
    assert dumper(None) is None
    assert dumper('b') == 'b'
