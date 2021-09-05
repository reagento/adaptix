from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.core import CannotProvide
from dataclass_factory_30.low_level.fields import (
    ClassInitFieldsProvider,
    NoDefault,
    DefaultValue,
    FieldRM,
    InputFieldsFigure,
    ExtraVariant
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


class Invalid1:
    def __init__(self, a, /, b):
        self.a = a
        self.b = b


VALID_FIELDS = [
    FieldRM(
        type=Any,
        field_name='a',
        default=NoDefault(field_is_required=True),
        metadata=MappingProxyType({})
    ),
    FieldRM(
        type=int,
        field_name='b',
        default=NoDefault(field_is_required=True),
        metadata=MappingProxyType({})
    ),
    FieldRM(
        type=str,
        field_name='c',
        default=DefaultValue('abc'),
        metadata=MappingProxyType({})
    ),
    FieldRM(
        type=Any,
        field_name='d',
        default=NoDefault(field_is_required=True),
        metadata=MappingProxyType({})
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
            extra=ExtraVariant.KWARGS,
            fields=VALID_FIELDS,
        )
    )


def test_fail():
    with pytest.raises(CannotProvide):
        ClassInitFieldsProvider()._get_input_fields_figure(Invalid1)
