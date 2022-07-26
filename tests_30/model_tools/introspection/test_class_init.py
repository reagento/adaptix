from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.model_tools import (
    DefaultValue,
    ExtraKwargs,
    InputField,
    InputFigure,
    IntrospectionError,
    NoDefault,
    ParamKind,
    get_class_init_input_figure,
)


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


VALID_FIELDS = (
    InputField(
        type=Any,
        name='a',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
        param_name='a',
    ),
    InputField(
        type=int,
        name='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
        param_name='b',
    ),
    InputField(
        type=str,
        name='c',
        default=DefaultValue('abc'),
        is_required=False,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
        param_name='c',
    ),
    InputField(
        type=Any,
        name='d',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.KW_ONLY,
        param_name='d',
    ),
)


def test_extra_none():
    assert (
        get_class_init_input_figure(Valid1)
        ==
        InputFigure(
            constructor=Valid1,
            extra=None,
            fields=VALID_FIELDS,
        )
    )


def test_extra_kwargs():
    assert (
        get_class_init_input_figure(Valid2Kwargs)
        ==
        InputFigure(
            constructor=Valid2Kwargs,
            extra=ExtraKwargs(),
            fields=VALID_FIELDS,
        )
    )


def test_pos_only():
    class HasPosOnly:
        def __init__(self, a, /, b):
            self.a = a
            self.b = b

    assert (
        get_class_init_input_figure(HasPosOnly)
        ==
        InputFigure(
            constructor=HasPosOnly,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_ONLY,
                    param_name='a',
                ),
                InputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
            ),
        )
    )

    class HasPosOnlyWithDefault:
        def __init__(self, a=None, b=None, /):
            self.a = a
            self.b = b

    assert (
        get_class_init_input_figure(HasPosOnlyWithDefault)
        ==
        InputFigure(
            constructor=HasPosOnlyWithDefault,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=DefaultValue(None),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_ONLY,
                    param_name='a',
                ),
                InputField(
                    type=Any,
                    name='b',
                    default=DefaultValue(None),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_ONLY,
                    param_name='b',
                ),
            ),
        )
    )


def test_var_arg():
    class HasVarArg:
        def __init__(self, a, b, *args):
            self.a = a
            self.b = b
            self.args = args

    with pytest.raises(IntrospectionError):
        get_class_init_input_figure(HasVarArg)
