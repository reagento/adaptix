from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union

import pytest
from tests_helpers import TestRetort, raises_exc, with_cause, with_notes

from adaptix import CannotProvide, DebugTrail, NoSuitableProvider, Retort, dumper, loader
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.load_error import BadVariantError, LoadError, TypeLoadError, UnionLoadError
from adaptix._internal.morphing.generic_provider import LiteralProvider, UnionProvider


@dataclass
class Book:
    price: int
    author: Union[str, List[str]]


def make_loader(tp: type):
    def tp_loader(data):
        if isinstance(data, tp):
            return data
        raise TypeLoadError(tp, data)

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


def test_loading(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Union[int, str],
    )

    assert loader_(1) == 1
    assert loader_('a') == 'a'

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            LoadError(),
            lambda: loader_([]),
        )
    elif debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
        raises_exc(
            UnionLoadError(
                f'while loading {Union[int, str]}',
                [
                    TypeLoadError(int, []),
                    TypeLoadError(str, []),
                ]
            ),
            lambda: loader_([]),
        )


def bad_string_loader(data):
    if isinstance(data, str):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def bad_int_loader(data):
    if isinstance(data, int):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def test_loading_unexpected_error(retort, strict_coercion, debug_trail):
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).extend(
        recipe=[
            loader(str, bad_string_loader),
            loader(int, bad_int_loader),
        ],
    ).get_loader(
        Union[int, str],
    )

    if debug_trail in (DebugTrail.DISABLE, DebugTrail.FIRST):
        raises_exc(
            TypeError(),
            lambda: loader_([]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                f'while loading {Union[int, str]}',
                [
                    TypeError(),
                    TypeError(),
                ]
            ),
            lambda: loader_([]),
        )


def test_dumping(retort, debug_trail):
    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[int, str]
    )

    assert dumper_(1) == 1
    assert dumper_('a') == 'a'

    raises_exc(
        KeyError(list),
        lambda: dumper_([]),
    )


def test_dumping_of_none(retort, debug_trail):
    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[int, str, None]
    )

    assert dumper_(1) == 1
    assert dumper_('a') == 'a'
    assert dumper_(None) is None

    raises_exc(
        KeyError(list),
        lambda: dumper_([]),
    )


def test_dumping_subclass(retort, debug_trail):
    @dataclass
    class Parent:
        foo: int

    @dataclass
    class Child(Parent):
        bar: int

    dumper_ = Retort(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[Parent, str]
    )

    assert dumper_(Parent(foo=1)) == {'foo': 1}
    assert dumper_(Child(foo=1, bar=2)) == {'foo': 1}
    assert dumper_('a') == 'a'

    raises_exc(
        KeyError(list),
        lambda: dumper_([]),
    )


def test_optional_dumping(retort, debug_trail):
    opt_dumper = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Optional[str],
    )

    assert opt_dumper('a') == 'a'
    assert opt_dumper(None) is None

    raises_exc(
        TypeError(list),
        lambda: opt_dumper([]),
    )


def test_bad_optional_dumping(retort, debug_trail):
    raises_exc(
        with_cause(
            NoSuitableProvider(
                f'Cannot produce dumper for type {Union[int, Callable[[int], str]]}',
            ),
            with_notes(
                CannotProvide(
                    message=f'All cases of union must be class, but found {[Callable[[int], str]]}',
                    is_demonstrative=True,
                    is_terminal=True,
                ),
                f'Location: type={Union[int, Callable[[int], str]]}'
            ),
        ),
        func=lambda: (
            retort.replace(
                debug_trail=debug_trail,
            ).get_dumper(
                Union[int, Callable[[int], str]],
            )
        ),
    )


def test_literal(strict_coercion, debug_trail):
    retort = TestRetort(
        recipe=[
            LiteralProvider(),
            UnionProvider(),
            make_loader(type(None)),
            make_dumper(type(None)),
        ]
    )

    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal['a', None],
    )

    assert loader_('a') == 'a'
    assert loader_(None) is None

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            BadVariantError({'a'}, 'b'),
            lambda: loader_('b'),
        )
    elif debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
        raises_exc(
            UnionLoadError(
                f'while loading {Literal["a", None]}',
                [TypeLoadError(None, 'b'), BadVariantError({'a'}, 'b')]
            ),
            lambda: loader_('b'),
        )

    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Literal['a', None],
    )

    assert dumper_('a') == 'a'
    assert dumper_(None) is None
    assert dumper_('b') == 'b'
