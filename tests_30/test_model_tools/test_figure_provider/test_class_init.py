from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.feature_requirement import has_pos_only_params
from dataclass_factory_30.model_tools import InputField, NoDefault, ParamKind, DefaultValue, \
    get_class_init_input_figure, InputFigure, ExtraKwargs, IntrospectionError


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
    ),
    InputField(
        type=int,
        name='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
    ),
    InputField(
        type=str,
        name='c',
        default=DefaultValue('abc'),
        is_required=False,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
    ),
    InputField(
        type=Any,
        name='d',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.KW_ONLY,
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


@has_pos_only_params
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
                ),
                InputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
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
