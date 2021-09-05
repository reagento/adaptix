from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.core import CannotProvide
from dataclass_factory_30.low_level.fields import ClassInitFieldsProvider, NoDefault, DefaultValue, TypeFieldRequest


class Valid1:
    def __init__(self, a, b: int, c: str = 'abc', *, d):
        self.a = a
        self.b = b
        self.c = c
        self.d = d


class Invalid1:
    def __init__(self, a, /, b):
        self.a = a
        self.b = b


def test_good():
    assert (
        ClassInitFieldsProvider()._get_fields(Valid1)
        ==
        [
            TypeFieldRequest(
                type=Any,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=int,
                field_name='b',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=str,
                field_name='c',
                default=DefaultValue('abc'),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=Any,
                field_name='d',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
        ]
    )


def test_fail():
    with pytest.raises(CannotProvide):
        ClassInitFieldsProvider()._get_fields(Invalid1)
