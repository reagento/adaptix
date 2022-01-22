from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.feature_requirement import has_pos_only_params
from dataclass_factory_30.provider import DefaultValue, NoDefault, CannotProvide
from dataclass_factory_30.provider.fields import (
    ClassInitFieldsProvider,
    InputFieldRM,
    InputFieldsFigure,
    ExtraKwargs
)
from dataclass_factory_30.provider.request_cls import ParamKind


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


VALID_FIELDS = [
    InputFieldRM(
        type=Any,
        field_name='a',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
    ),
    InputFieldRM(
        type=int,
        field_name='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
    ),
    InputFieldRM(
        type=str,
        field_name='c',
        default=DefaultValue('abc'),
        is_required=False,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.POS_OR_KW,
    ),
    InputFieldRM(
        type=Any,
        field_name='d',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({}),
        param_kind=ParamKind.KW_ONLY,
    ),
]


def test_extra_none():
    assert (
        ClassInitFieldsProvider()._get_input_fields_figure(Valid1)
        ==
        InputFieldsFigure(
            extra=None,
            fields=VALID_FIELDS,
        )
    )


def test_extra_kwargs():
    assert (
        ClassInitFieldsProvider()._get_input_fields_figure(Valid2Kwargs)
        ==
        InputFieldsFigure(
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
        ClassInitFieldsProvider()._get_input_fields_figure(HasPosOnly)
        ==
        InputFieldsFigure(
            extra=None,
            fields=[
                InputFieldRM(
                    type=Any,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_ONLY,
                ),
                InputFieldRM(
                    type=Any,
                    field_name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ],
        )
    )


def test_var_arg():
    class HasVarArg:
        def __init__(self, a, b, *args):
            self.a = a
            self.b = b
            self.args = args

    with pytest.raises(CannotProvide):
        ClassInitFieldsProvider()._get_input_fields_figure(
            HasVarArg
        )
