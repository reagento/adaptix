from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.low_level.fields import NamedTupleFieldsProvider, TypeFieldRequest, DefaultValue, NoDefault

FooAB = namedtuple('FooAB', 'a b')
FooBA = namedtuple('FooBA', 'b a')


def test_order():
    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooAB)
        ==
        [
            TypeFieldRequest(
                type=Any,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=Any,
                field_name='b',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
        ]
    )

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooBA)
        ==
        [
            TypeFieldRequest(
                type=Any,
                field_name='b',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=Any,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
        ]
    )


def func():
    return 0


FooDefs = namedtuple('FooDefs', 'a b c', defaults=[0, func])


def test_defaults():
    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooDefs)
        ==
        [
            TypeFieldRequest(
                type=Any,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=Any,
                field_name='b',
                default=DefaultValue(0),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=Any,
                field_name='c',
                default=DefaultValue(func),
                metadata=MappingProxyType({})
            ),
        ]
    )


BarA = NamedTuple('BarA', a=int, b=str)

# ClassVar do not supported in NamedTuple


class BarB(NamedTuple):
    a: int
    b: str = 'abc'


def test_hinted_namedtuple():
    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarA)
        ==
        [
            TypeFieldRequest(
                type=int,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=str,
                field_name='b',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
        ]
    )

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarB)
        ==
        [
            TypeFieldRequest(
                type=int,
                field_name='a',
                default=NoDefault(field_is_required=True),
                metadata=MappingProxyType({})
            ),
            TypeFieldRequest(
                type=str,
                field_name='b',
                default=DefaultValue('abc'),
                metadata=MappingProxyType({})
            ),
        ]
    )
