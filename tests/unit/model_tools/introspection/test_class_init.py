import typing
from types import MappingProxyType
from typing import Any
from unittest.mock import ANY

import pytest
from tests_helpers import requires

from adaptix._internal.feature_requirement import HAS_ANNOTATED
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
from adaptix._internal.model_tools.introspection.class_init import get_class_init_shape


class Valid1:
    def __init__(self, a, b: int, c: str = 'abc', *, d):
        self.a = a
        self.b = b
        self.c = c
        self.d = d


class Valid2Kwargs:
    def __init__(self, a, b: int, c: str = 'abc', *, d, **data):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.data = data


class Valid2KwargsTyped:
    def __init__(self, a, b: int, c: str = 'abc', *, d, **data: str):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.data = data


VALID_FIELDS = (
    InputField(
        type=Any,
        id='a',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        original=ANY,
    ),
    InputField(
        type=int,
        id='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        original=ANY,
    ),
    InputField(
        type=str,
        id='c',
        default=DefaultValue('abc'),
        is_required=False,
        metadata=MappingProxyType({}),
        original=ANY,
    ),
    InputField(
        type=Any,
        id='d',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        original=ANY,
    ),
)
VALID_PARAMS = (
    Param(
        field_id='a',
        name='a',
        kind=ParamKind.POS_OR_KW,
    ),
    Param(
        field_id='b',
        name='b',
        kind=ParamKind.POS_OR_KW,
    ),
    Param(
        field_id='c',
        name='c',
        kind=ParamKind.POS_OR_KW,
    ),
    Param(
        field_id='d',
        name='d',
        kind=ParamKind.KW_ONLY,
    ),
)


def test_extra_none():
    assert (
        get_class_init_shape(Valid1)
        ==
        Shape(
            input=InputShape(
                constructor=Valid1,
                kwargs=None,
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
                params=VALID_PARAMS,
            ),
            output=None,
        )
    )


def test_extra_kwargs():
    assert (
        get_class_init_shape(Valid2Kwargs)
        ==
        Shape(
            input=InputShape(
                constructor=Valid2Kwargs,
                kwargs=ParamKwargs(Any),
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
                params=VALID_PARAMS,
            ),
            output=None,
        )

    )

    assert (
        get_class_init_shape(Valid2KwargsTyped)
        ==
        Shape(
            input=InputShape(
                constructor=Valid2KwargsTyped,
                kwargs=ParamKwargs(str),
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
                params=VALID_PARAMS,
            ),
            output=None,
        )
    )


def test_pos_only():
    class HasPosOnly:
        def __init__(self, a, /, b):
            self.a = a
            self.b = b

    assert (
        get_class_init_shape(HasPosOnly)
        ==
        Shape(
            input=InputShape(
                constructor=HasPosOnly,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_ONLY,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=None,
        )

    )

    class HasPosOnlyWithDefault:
        def __init__(self, a=None, b=None, /):
            self.a = a
            self.b = b

    assert (
        get_class_init_shape(HasPosOnlyWithDefault)
        ==
        Shape(
            input=InputShape(
                constructor=HasPosOnlyWithDefault,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id='a',
                        default=DefaultValue(None),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id='b',
                        default=DefaultValue(None),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_ONLY,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.POS_ONLY,
                    ),
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=None,
        )
    )


def test_var_arg():
    class HasVarArg:
        def __init__(self, a, b, *args):
            self.a = a
            self.b = b
            self.args = args

    with pytest.raises(IntrospectionImpossible):
        get_class_init_shape(HasVarArg)


@requires(HAS_ANNOTATED)
def test_annotated():
    class WithAnnotated:
        def __init__(self, a: typing.Annotated[int, 'metadata']):
            pass

    assert (
        get_class_init_shape(WithAnnotated)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'a'}),
            ),
            output=None,
        )
    )
