import typing
from types import MappingProxyType
from typing import Any

import pytest

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools import (
    DefaultValue,
    Figure,
    InputField,
    InputFigure,
    IntrospectionImpossible,
    NoDefault,
    ParamKind,
    get_class_init_figure,
)
from adaptix._internal.model_tools.definitions import ParamKwargs
from tests_helpers import requires


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
        param_kind=ParamKind.POS_OR_KW,
        param_name='a',
    ),
    InputField(
        type=int,
        id='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
        param_name='b',
    ),
    InputField(
        type=str,
        id='c',
        default=DefaultValue('abc'),
        is_required=False,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
        param_name='c',
    ),
    InputField(
        type=Any,
        id='d',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.KW_ONLY,
        param_name='d',
    ),
)


def test_extra_none():
    assert (
        get_class_init_figure(Valid1)
        ==
        Figure(
            input=InputFigure(
                constructor=Valid1,
                kwargs=None,
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
            ),
            output=None,
        )
    )


def test_extra_kwargs():
    assert (
        get_class_init_figure(Valid2Kwargs)
        ==
        Figure(
            input=InputFigure(
                constructor=Valid2Kwargs,
                kwargs=ParamKwargs(Any),
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
            ),
            output=None,
        )

    )

    assert (
        get_class_init_figure(Valid2KwargsTyped)
        ==
        Figure(
            input=InputFigure(
                constructor=Valid2KwargsTyped,
                kwargs=ParamKwargs(str),
                fields=VALID_FIELDS,
                overriden_types=frozenset(fld.id for fld in VALID_FIELDS),
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
        get_class_init_figure(HasPosOnly)
        ==
        Figure(
            input=InputFigure(
                constructor=HasPosOnly,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_ONLY,
                        param_name='a',
                    ),
                    InputField(
                        type=Any,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
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
        get_class_init_figure(HasPosOnlyWithDefault)
        ==
        Figure(
            input=InputFigure(
                constructor=HasPosOnlyWithDefault,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id='a',
                        default=DefaultValue(None),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_ONLY,
                        param_name='a',
                    ),
                    InputField(
                        type=Any,
                        id='b',
                        default=DefaultValue(None),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_ONLY,
                        param_name='b',
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
        get_class_init_figure(HasVarArg)


@requires(HAS_ANNOTATED)
def test_annotated():
    class WithAnnotated:
        def __init__(self, a: typing.Annotated[int, 'metadata']):
            pass

    assert (
        get_class_init_figure(WithAnnotated)
        ==
        Figure(
            input=InputFigure(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='a',
                    ),
                ),
                overriden_types=frozenset({'a'}),
            ),
            output=None,
        )
    )
