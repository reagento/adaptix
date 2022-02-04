from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.provider import DefaultValue, NoDefault
from dataclass_factory_30.provider.fields_figure import (
    NamedTupleFieldsProvider,
    FieldRM,
    InputFieldsFigure,
    OutputFieldsFigure,
    GetterKind,
    _to_inp,
)
from dataclass_factory_30.provider.request_cls import ParamKind, InputFieldRM

FooAB = namedtuple('FooAB', 'a b')
FooBA = namedtuple('FooBA', 'b a')


def test_order_ab():
    fields = (
        FieldRM(
            type=Any,
            field_name='a',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='b',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
    )

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooAB)
        ==
        InputFieldsFigure(
            constructor=FooAB,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
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
    fields = (
        FieldRM(
            type=Any,
            field_name='b',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            field_name='a',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
    )

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooBA)
        ==
        InputFieldsFigure(
            constructor=FooBA,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
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
    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(FooDefs)
        ==
        InputFieldsFigure(
            constructor=FooDefs,
            extra=None,
            fields=(
                InputFieldRM(
                    type=Any,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=Any,
                    field_name='b',
                    default=DefaultValue(0),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=Any,
                    field_name='c',
                    default=DefaultValue(func),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(FooDefs)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=(
                FieldRM(
                    type=Any,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=Any,
                    field_name='b',
                    default=DefaultValue(0),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=Any,
                    field_name='c',
                    default=DefaultValue(func),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
            ),
        )
    )


BarA = NamedTuple('BarA', a=int, b=str)


def test_class_hinted_namedtuple():
    fields = (
        FieldRM(
            type=int,
            field_name='a',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=str,
            field_name='b',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
    )

    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarA)
        ==
        InputFieldsFigure(
            constructor=BarA,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
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


# ClassVar do not supported in NamedTuple

class BarB(NamedTuple):
    a: int
    b: str = 'abc'


def test_hinted_namedtuple():
    assert (
        NamedTupleFieldsProvider()._get_input_fields_figure(BarB)
        ==
        InputFieldsFigure(
            constructor=BarB,
            extra=None,
            fields=(
                InputFieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=str,
                    field_name='b',
                    default=DefaultValue('abc'),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )

    assert (
        NamedTupleFieldsProvider()._get_output_fields_figure(BarB)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=(
                FieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=str,
                    field_name='b',
                    default=DefaultValue('abc'),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
            ),
        )
    )
