from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.low_level.fields import TypedDictInputFieldsProvider, FieldsProvisionCtx, NoDefault


class Foo(TypedDict, total=True):
    a: int
    b: str


class Bar(TypedDict, total=False):
    a: int
    b: str


def test_total():
    assert (
        TypedDictInputFieldsProvider()._get_fields(Foo)
        ==
        [
            FieldsProvisionCtx(
                type=int,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            FieldsProvisionCtx(
                type=str,
                field_name='b',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
        ]
    )


def test_not_total():
    assert (
        TypedDictInputFieldsProvider()._get_fields(Bar)
        ==
        [
            FieldsProvisionCtx(
                type=int,
                field_name='a',
                default=NoDefault(field_is_required=False),
                metadata=MappingProxyType({})
            ),
            FieldsProvisionCtx(
                type=str,
                field_name='b',
                default=NoDefault(field_is_required=False),
                metadata=MappingProxyType({})
            ),
        ]
    )
