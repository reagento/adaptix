from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from dataclass_factory_30.model_tools import (
    InputFigure, InputField, NoDefault, ParamKind,
    OutputField, AttrAccessor, OutputFigure, DefaultValue,
    get_named_tuple_input_figure,
    get_named_tuple_output_figure,
)
FooAB = namedtuple('FooAB', 'a b')
FooBA = namedtuple('FooBA', 'b a')


def test_order_ab():
    assert (
        get_named_tuple_input_figure(FooAB)
        ==
        InputFigure(
            constructor=FooAB,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    param_kind=ParamKind.POS_OR_KW,
                    metadata=MappingProxyType({}),
                ),
                InputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    param_kind=ParamKind.POS_OR_KW,
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )

    assert (
        get_named_tuple_output_figure(FooAB)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    accessor=AttrAccessor('b', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


def test_order_ba():
    assert (
        get_named_tuple_input_figure(FooBA)
        ==
        InputFigure(
            constructor=FooBA,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )

    assert (
        get_named_tuple_output_figure(FooBA)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=Any,
                    name='b',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('b', is_required=True),
                ),
                OutputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('a', is_required=True),
                ),
            ),
        )
    )


def func():
    return 0


FooDefs = namedtuple('FooDefs', 'a b c', defaults=[0, func])


def test_defaults():
    assert (
        get_named_tuple_input_figure(FooDefs)
        ==
        InputFigure(
            constructor=FooDefs,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputField(
                    type=Any,
                    name='b',
                    default=DefaultValue(0),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputField(
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
        get_named_tuple_output_figure(FooDefs)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('a', is_required=True),
                ),
                OutputField(
                    type=Any,
                    name='b',
                    default=DefaultValue(0),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('b', is_required=True),
                ),
                OutputField(
                    type=Any,
                    name='c',
                    default=DefaultValue(func),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('c', is_required=True),
                ),
            ),
        )
    )


BarA = NamedTuple('BarA', a=int, b=str)


def test_class_hinted_namedtuple():
    assert (
        get_named_tuple_input_figure(BarA)
        ==
        InputFigure(
            constructor=BarA,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )

    assert (
        get_named_tuple_output_figure(BarA)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('a', is_required=True),
                ),
                OutputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('b', is_required=True),
                ),
            ),
        )
    )


# ClassVar is not supported in NamedTuple

class BarB(NamedTuple):
    a: int
    b: str = 'abc'


def test_hinted_namedtuple():
    assert (
        get_named_tuple_input_figure(BarB)
        ==
        InputFigure(
            constructor=BarB,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputField(
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
        get_named_tuple_output_figure(BarB)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('a', is_required=True),
                ),
                OutputField(
                    type=str,
                    name='b',
                    default=DefaultValue('abc'),
                    metadata=MappingProxyType({}),
                    accessor=AttrAccessor('b', is_required=True),
                ),
            ),
        )
    )
