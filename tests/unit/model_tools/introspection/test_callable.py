import typing
from types import MappingProxyType
from typing import Tuple, TypedDict
from unittest.mock import ANY

import pytest
from tests_helpers import requires

from adaptix._internal.feature_requirement import HAS_PY_312
from adaptix._internal.model_tools.definitions import (
    DefaultValue,
    InputField,
    InputShape,
    IntrospectionImpossible,
    NoDefault,
    Param,
    ParamKind,
    ParamKwargs,
    Shape,
)
from adaptix._internal.model_tools.introspection.callable import get_callable_shape


def test_introspection_impossible():
    pytest.raises(IntrospectionImpossible, lambda: get_callable_shape(Tuple))


def test_simple():
    def foo(a: int, /, b: int, c: str = '', *, d: int = 0, e: str, **kwargs: int) -> int:
        pass

    assert get_callable_shape(foo) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id='a',
                    type=int,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
                InputField(
                    id='b',
                    type=int,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
                InputField(
                    id='c',
                    type=str,
                    default=DefaultValue(value=''),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=False
                ),
                InputField(
                    id='d',
                    type=int,
                    default=DefaultValue(value=0),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=False
                ),
                InputField(
                    id='e',
                    type=str,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
            ),
            overriden_types=frozenset({'a', 'b', 'c', 'd', 'e'}),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_ONLY
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=ParamKind.POS_OR_KW
                ),
                Param(
                    field_id='c',
                    name='c',
                    kind=ParamKind.POS_OR_KW
                ),
                Param(
                    field_id='d',
                    name='d',
                    kind=ParamKind.KW_ONLY
                ),
                Param(
                    field_id='e',
                    name='e',
                    kind=ParamKind.KW_ONLY
                ),
            ),
            kwargs=ParamKwargs(type=int),
            constructor=foo,
        ),
        output=None,
    )


@requires(HAS_PY_312)
def test_unpacking_empty():
    class Bar(TypedDict):
        pass

    def foo(a: int, b: str = '', **kwargs: typing.Unpack[Bar]) -> int:
        pass

    assert get_callable_shape(foo) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id='a',
                    type=int,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
                InputField(
                    id='b',
                    type=str,
                    default=DefaultValue(value=''),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=False
                ),
            ),
            overriden_types=frozenset({'b', 'a'}),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_OR_KW
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=ParamKind.POS_OR_KW
                ),
            ),
            kwargs=None,
            constructor=foo,
        ),
        output=None,
    )


@requires(HAS_PY_312)
def test_unpacking_simple():
    class Bar(TypedDict):
        c: int
        d: str

    def foo(a: int, b: str = '', **kwargs: typing.Unpack[Bar]) -> int:
        pass

    assert get_callable_shape(foo) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id='a',
                    type=int,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
                InputField(
                    id='b',
                    type=str,
                    default=DefaultValue(value=''),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=False
                ),
                InputField(
                    id='c',
                    type=int,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
                InputField(
                    id='d',
                    type=str,
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    original=ANY,
                    is_required=True
                ),
            ),
            overriden_types=frozenset({'b', 'a'}),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_OR_KW
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=ParamKind.POS_OR_KW
                ),
                Param(
                    field_id='c',
                    name='c',
                    kind=ParamKind.KW_ONLY
                ),
                Param(
                    field_id='d',
                    name='d',
                    kind=ParamKind.KW_ONLY
                ),
            ),
            kwargs=None,
            constructor=foo,
        ),
        output=None,
    )
