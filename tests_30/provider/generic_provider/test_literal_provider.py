from typing import Literal
from uuid import uuid4

import pytest

from dataclass_factory_30.provider import LiteralProvider, ParseError, ParserRequest
from tests_30.test_helpers import TestFactory, parametrize_bool, raises_instance


@pytest.fixture
def factory():
    return TestFactory(
        recipe=[
            LiteralProvider(),
        ]
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_parser_base(factory, strict_coercion, debug_path):
    parser = factory.provide(
        ParserRequest(
            type=Literal["a", "b", 10],
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser("a") == "a"
    assert parser("b") == "b"
    assert parser(10) == 10

    raises_instance(
        ParseError(),
        lambda: parser("c")
    )


def rnd():
    return uuid4().hex


def _is_exact_zero(arg):
    return type(arg) == int and arg == 0


def _is_exact_one(arg):
    return type(arg) == int and arg == 1


@parametrize_bool('debug_path')
def test_strict_coercion(factory, debug_path):
    # Literal definition could have very strange behavior
    # due to type cache and 0 == False, 1 == True,
    # so Literal[0, 1] sometimes returns Literal[False, True]
    # and vice versa.
    # We add a random string at the end to suppress caching
    parser_int = factory.provide(
        ParserRequest(
            type=Literal[0, 1, rnd()],  # noqa
            strict_coercion=True,
            debug_path=debug_path,
        )
    )

    assert _is_exact_zero(parser_int(0))
    assert _is_exact_one(parser_int(1))

    raises_instance(
        ParseError(),
        lambda: parser_int(False)
    )
    raises_instance(
        ParseError(),
        lambda: parser_int(True)
    )

    parser_bool = factory.provide(
        ParserRequest(
            type=Literal[False, True, rnd()],  # noqa
            strict_coercion=True,
            debug_path=debug_path,
        )
    )

    assert parser_bool(False) is False
    assert parser_bool(True) is True

    raises_instance(
        ParseError(),
        lambda: parser_bool(0)
    )
    raises_instance(
        ParseError(),
        lambda: parser_bool(1)
    )
