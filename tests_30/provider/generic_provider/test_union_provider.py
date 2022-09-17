import re
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union

import pytest

from dataclass_factory_30.facade import Factory, parser, serializer
from dataclass_factory_30.provider import (
    LiteralProvider,
    ParseError,
    ParserRequest,
    SerializerRequest,
    TypeParseError,
    UnionParseError,
    UnionProvider,
)
from tests_helpers import TestFactory, parametrize_bool, raises_path


@dataclass
class Book:
    price: int
    author: Union[str, List[str]]


def test_union_at_field():
    data = {
        "price": 123,
        "author": "meow"
    }

    factory = Factory()
    factory.parser(Book)(data)


def make_parser(tp: type):
    def tp_parser(data):
        if isinstance(data, tp):
            return data
        raise TypeParseError(tp)

    return parser(tp, tp_parser)


def make_serializer(tp: type):
    def tp_serializer(data):
        if isinstance(data, tp):
            return data
        raise TypeError(type(data))

    return serializer(tp, tp_serializer)


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            UnionProvider(),
            make_parser(str),
            make_parser(int),
            make_serializer(str),
            make_serializer(int),
            make_serializer(type(None)),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_parsing(factory, strict_coercion, debug_path):
    parser = factory.provide(
        ParserRequest(
            type=Union[int, str],
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser(1) == 1
    assert parser('a') == 'a'

    if debug_path:
        raises_path(
            UnionParseError,
            lambda: parser([]),
            path=[],
            match=re.escape(
                "[TypeParseError(expected_type=<class 'int'>), TypeParseError(expected_type=<class 'str'>)]"
            ),
        )
    else:
        raises_path(
            ParseError,
            lambda: parser([]),
            path=[],
            match='',
        )


@parametrize_bool('debug_path')
def test_serializing(factory, debug_path):
    serializer = factory.provide(
        SerializerRequest(
            type=Union[int, str],
            debug_path=debug_path,
        )
    )

    assert serializer(1) == 1
    assert serializer('a') == 'a'

    raises_path(
        KeyError,
        lambda: serializer([]),
        path=[],
        match=re.escape("<class 'list'>"),
    )


@parametrize_bool('debug_path')
def test_opt_serializing(factory, debug_path):
    opt_serializer = factory.provide(
        SerializerRequest(
            type=Optional[str],
            debug_path=debug_path,
        )
    )

    assert opt_serializer('a') == 'a'
    assert opt_serializer(None) is None

    raises_path(
        TypeError,
        lambda: opt_serializer([]),
        path=[],
        match=re.escape("<class 'list'>"),
    )


@parametrize_bool('debug_path')
def test_bad_opt_serializing(factory, debug_path):
    raises_path(
        ValueError,
        lambda: factory.provide(
            SerializerRequest(
                type=Union[int, Callable[[int], str]],
                debug_path=debug_path,
            )
        ),
        path=[],
        match=re.escape(
            "Can not create serializer for typing.Union[int, typing.Callable[[int], str]]."
            " All cases of union must be class, but found [typing.Callable[[int], str]]"
        ),
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_literal(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[
            LiteralProvider(),
            UnionProvider(),
            make_parser(type(None)),
            make_serializer(type(None)),
        ]
    )

    parser = factory.provide(
        ParserRequest(
            type=Literal['a', None],
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('a') == 'a'
    assert parser(None) is None

    if debug_path:
        raises_path(
            UnionParseError([TypeParseError(type(None)), ParseError()]),
            lambda: parser('b'),
            path=[],
        )
    else:
        raises_path(
            ParseError(),
            lambda: parser('b'),
            path=[],
        )

    serializer = factory.provide(
        SerializerRequest(
            type=Literal['a', None],
            debug_path=debug_path,
        )
    )

    assert serializer('a') == 'a'
    assert serializer(None) is None
    assert serializer('b') == 'b'
