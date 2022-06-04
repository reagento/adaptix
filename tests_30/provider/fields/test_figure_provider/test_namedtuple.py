from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.provider import DefaultValue, NoDefault, NamedTupleFigureProvider, InputFigure, \
    OutputFigure
from dataclass_factory_30.provider.fields.figure_provider import _to_inp, _to_out
from dataclass_factory_30.provider.request_cls import ParamKind, InputFieldRM, AccessKind, OutputFieldRM, FieldRM

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
        NamedTupleFigureProvider()._get_input_figure(FooAB)
        ==
        InputFigure(
            constructor=FooAB,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
        )
    )

    assert (
        NamedTupleFigureProvider()._get_output_figure(FooAB)
        ==
        OutputFigure(
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
        NamedTupleFigureProvider()._get_input_figure(FooBA)
        ==
        InputFigure(
            constructor=FooBA,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
        )
    )

    assert (
        NamedTupleFigureProvider()._get_output_figure(FooBA)
        ==
        OutputFigure(
            extra=None,
            fields=_to_out(AccessKind.ATTR, fields),
        )
    )


def func():
    return 0


FooDefs = namedtuple('FooDefs', 'a b c', defaults=[0, func])


def test_defaults():
    assert (
        NamedTupleFigureProvider()._get_input_figure(FooDefs)
        ==
        InputFigure(
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
        NamedTupleFigureProvider()._get_output_figure(FooDefs)
        ==
        OutputFigure(
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
        NamedTupleFigureProvider()._get_input_figure(BarA)
        ==
        InputFigure(
            constructor=BarA,
            extra=None,
            fields=_to_inp(ParamKind.POS_OR_KW, fields),
        )
    )

    assert (
        NamedTupleFigureProvider()._get_output_figure(BarA)
        ==
        OutputFigure(
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
        NamedTupleFigureProvider()._get_input_figure(BarB)
        ==
        InputFigure(
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
        NamedTupleFigureProvider()._get_output_figure(BarB)
        ==
        OutputFigure(
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
