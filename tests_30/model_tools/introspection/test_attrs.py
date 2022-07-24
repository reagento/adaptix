from types import MappingProxyType
from typing import Any

import pytest

from dataclass_factory_30.model_tools import (
    AttrAccessor,
    DefaultFactory,
    DefaultValue,
    ExtraKwargs,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_attrs_input_figure,
    get_attrs_output_figure,
)

pytest.importorskip("attrs")

import attr
from attrs import define, field


@define
class NewStyle:
    a: int
    _b: str
    c: str = field(init=False)
    d: int = field(kw_only=True)

    e: int = 1
    f: int = field(default=2)
    g: list = field(factory=list)
    h: str = field(default='', metadata={'meta': 'data'})


def test_new_style_input():
    assert (
        get_attrs_input_figure(NewStyle)
        ==
        InputFigure(
            constructor=NewStyle,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    type=str,
                    name='_b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
                InputField(
                    type=int,
                    name='e',
                    default=DefaultValue(1),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='e',
                ),
                InputField(
                    type=int,
                    name='f',
                    default=DefaultValue(2),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='f',
                ),
                InputField(
                    type=list,
                    name='g',
                    default=DefaultFactory(list),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='g',
                ),
                InputField(
                    type=str,
                    name='h',
                    default=DefaultValue(''),
                    is_required=False,
                    metadata=MappingProxyType({'meta': 'data'}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='h',
                ),
                InputField(
                    type=int,
                    name='d',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='d',
                ),
            ),
        )
    )


def test_new_style_output():
    assert (
        get_attrs_output_figure(NewStyle)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=str,
                    name='_b',
                    default=NoDefault(),
                    accessor=AttrAccessor('_b', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=str,
                    name='c',
                    default=NoDefault(),
                    accessor=AttrAccessor('c', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='d',
                    default=NoDefault(),
                    accessor=AttrAccessor('d', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='e',
                    default=DefaultValue(1),
                    accessor=AttrAccessor('e', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='f',
                    default=DefaultValue(2),
                    accessor=AttrAccessor('f', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=list,
                    name='g',
                    default=DefaultFactory(list),
                    accessor=AttrAccessor('g', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=str,
                    name='h',
                    default=DefaultValue(''),
                    accessor=AttrAccessor('h', is_required=True),
                    metadata=MappingProxyType({'meta': 'data'}),
                ),
            ),
        )
    )


@attr.s
class OldStyle:
    a = attr.ib()
    b = attr.ib(type=int)
    c: int


def test_old_style_input():
    assert (
        get_attrs_input_figure(OldStyle)
        ==
        InputFigure(
            constructor=OldStyle,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    type=int,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
            ),
        )
    )


def test_old_style_output():
    assert (
        get_attrs_output_figure(OldStyle)
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
                    type=int,
                    name='b',
                    default=NoDefault(),
                    accessor=AttrAccessor('b', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


def int_factory():
    return 0


@define
class CustomInit:
    a: int
    b: int = field(factory=int_factory, metadata={'meta': 'data'})
    _c: int = field(kw_only=True)
    d: int = 10

    def __init__(self, a: str, b: str, c):
        self.__attrs_init__(int(a), int(b), int(c))


def test_custom_init_input():
    assert (
        get_attrs_input_figure(CustomInit)
        ==
        InputFigure(
            constructor=CustomInit,
            extra=None,
            fields=(
                InputField(
                    type=str,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({'meta': 'data'}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
                InputField(
                    type=Any,
                    name='_c',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='c',
                ),
            ),
        )
    )


def test_custom_init_output():
    assert (
        get_attrs_output_figure(CustomInit)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='b',
                    default=NoDefault(),
                    accessor=AttrAccessor('b', is_required=True),
                    metadata=MappingProxyType({'meta': 'data'}),
                ),
                OutputField(
                    type=int,
                    name='_c',
                    default=NoDefault(),
                    accessor=AttrAccessor('_c', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='d',
                    default=NoDefault(),
                    accessor=AttrAccessor('d', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


@define
class CustomInitUnknownParams:
    a: int
    other: dict

    def __init__(self, a: int, b: str, c: bytes):
        self.__attrs_init__(a, {'b': b, 'c': c})


def test_custom_init_unknown_params_input():
    assert (
        get_attrs_input_figure(CustomInitUnknownParams)
        ==
        InputFigure(
            constructor=CustomInitUnknownParams,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
                InputField(
                    type=bytes,
                    name='c',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='c',
                ),
            ),
        )
    )


def test_custom_init_unknown_params_output():
    assert (
        get_attrs_output_figure(CustomInitUnknownParams)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=dict,
                    name='other',
                    default=NoDefault(),
                    accessor=AttrAccessor('other', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


@define
class CustomInitKwargs:
    a: int

    def __init__(self, a: int, **kwargs):
        self.__attrs_init__(a)


def test_custom_init_kwargs():
    assert (
        get_attrs_input_figure(CustomInitKwargs)
        ==
        InputFigure(
            constructor=CustomInitKwargs,
            extra=ExtraKwargs(),
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            ),
        )
    )

    assert (
        get_attrs_output_figure(CustomInitKwargs)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


@define
class NoneAttr:
    a: None


def test_none_attr():
    assert (
        get_attrs_input_figure(NoneAttr)
        ==
        InputFigure(
            constructor=NoneAttr,
            extra=None,
            fields=(
                InputField(
                    type=type(None),
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            ),
        )
    )

    assert (
        get_attrs_output_figure(NoneAttr)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=type(None),
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )


@define
class NoneAttrCustomInit:
    a: None

    def __init__(self, a):
        self.__attrs_init__(a)


def test_none_attr_custom_init():
    assert (
        get_attrs_input_figure(NoneAttrCustomInit)
        ==
        InputFigure(
            constructor=NoneAttrCustomInit,
            extra=None,
            fields=(
                InputField(
                    type=Any,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            ),
        )
    )

    assert (
        get_attrs_output_figure(NoneAttrCustomInit)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=type(None),
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )
