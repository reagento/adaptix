from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.provider import DefaultValue, NoDefault
from dataclass_factory_30.provider.fields_figure import (
    NamedTupleFieldsProvider,
    FieldRM,
    InputFieldsFigure,
    OutputFieldsFigure,
    _to_inp, _to_out,
)
from dataclass_factory_30.provider.request_cls import ParamKind, InputFieldRM, AccessKind, OutputFieldRM

FooAB = namedtuple('FooAB', 'a b')
FooBA = namedtuple('FooBA', 'b a')


def test_order_ab():
    fields = (
        FieldRM(
            type=Any,
            name='a',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            name='b',
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
            extra=None,
            fields=_to_out(AccessKind.ATTR, fields),
        )
    )


def test_order_ba():
    fields = (
        FieldRM(
            type=Any,
            name='b',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=Any,
            name='a',
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
            extra=None,
            fields=_to_out(AccessKind.ATTR, fields),
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
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=Any,
                    name='b',
                    default=DefaultValue(0),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=Any,
                    name='c',
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
            extra=None,
            fields=(
                OutputFieldRM(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    access_kind=AccessKind.ATTR,
                ),
                OutputFieldRM(
                    type=Any,
                    name='b',
                    default=DefaultValue(0),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    access_kind=AccessKind.ATTR,
                ),
                OutputFieldRM(
                    type=Any,
                    name='c',
                    default=DefaultValue(func),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    access_kind=AccessKind.ATTR,
                ),
            ),
        )
    )


BarA = NamedTuple('BarA', a=int, b=str)


def test_class_hinted_namedtuple():
    fields = (
        FieldRM(
            type=int,
            name='a',
            default=NoDefault(),
            is_required=True,
            metadata=MappingProxyType({})
        ),
        FieldRM(
            type=str,
            name='b',
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
            extra=None,
            fields=_to_out(AccessKind.ATTR, fields),
        )
    )


# ClassVar is not supported in NamedTuple

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
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=str,
                    name='b',
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
            extra=None,
            fields=(
                OutputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    access_kind=AccessKind.ATTR,
                ),
                OutputFieldRM(
                    type=str,
                    name='b',
                    default=DefaultValue('abc'),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    access_kind=AccessKind.ATTR,
                ),
            ),
        )
    )
