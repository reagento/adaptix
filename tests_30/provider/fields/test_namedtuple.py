from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.provider import NoDefault, DefaultValue
from dataclass_factory_30.provider.fields import (
    NamedTupleFieldsProvider,
    FieldRM,
    InputFieldsFigure,
    OutputFieldsFigure,
    GetterKind
)

FooAB = namedtuple('FooAB', 'a b')
FooBA = namedtuple('FooBA', 'b a')


def test_order_ab():
    fields = [
        FieldRM(
            type=Any,
            field_name='a',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='b',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
    ]

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooAB)
        ==
        InputFieldsFigure(
            extra=None,
            fields=fields,
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(FooAB)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=fields,
        )
    )


def test_order_ba():
    fields = [
        FieldRM(
            type=Any,
            field_name='b',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='a',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
    ]

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooBA)
        ==
        InputFieldsFigure(
            extra=None,
            fields=fields,
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(FooBA)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=fields,
        )
    )


def func():
    return 0


FooDefs = namedtuple('FooDefs', 'a b c', defaults=[0, func])


def test_defaults():
    fields = [
        FieldRM(
            type=Any,
            field_name='a',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='b',
            default=DefaultValue(0),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='c',
            default=DefaultValue(func),
            metadata=MappingProxyType({})
        ),
    ]

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooDefs)
        ==
        InputFieldsFigure(
            extra=None,
            fields=fields,
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(FooDefs)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=fields,
        )
    )


BarA = NamedTuple('BarA', a=int, b=str)


# ClassVar do not supported in NamedTuple


class BarB(NamedTuple):
    a: int
    b: str = 'abc'


def test_class_hinted_namedtuple():
    fields = [
        FieldRM(
            type=int,
            field_name='a',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=str,
            field_name='b',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
    ]

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarA)
        ==
        InputFieldsFigure(
            extra=None,
            fields=fields,
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(BarA)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=fields,
        )
    )


def test_hinted_namedtuple():
    fields = [
        FieldRM(
            type=int,
            field_name='a',
            default=NoDefault(field_is_required=True),
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=str,
            field_name='b',
            default=DefaultValue('abc'),
            metadata=MappingProxyType({})
        ),
    ]

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarB)
        ==
        InputFieldsFigure(
            extra=None,
            fields=fields,
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(BarB)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=fields,
        )
    )