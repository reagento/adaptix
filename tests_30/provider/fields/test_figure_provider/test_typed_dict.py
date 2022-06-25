from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.provider import NoDefault, TypedDictFigureProvider, InputFigure, OutputFigure
from dataclass_factory_30.provider.definitions import ItemAccessor
from dataclass_factory_30.provider.request_cls import ParamKind, InputFieldRM, OutputFieldRM


class Foo(TypedDict, total=True):
    a: int
    b: str


class Bar(TypedDict, total=False):
    a: int
    b: str


def test_total_input():
    assert (
        TypedDictFigureProvider()._get_input_figure(Foo)
        ==
        InputFigure(
            constructor=Foo,
            extra=None,
            fields=(
                InputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
                InputFieldRM(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
            ),
        )
    )


def test_total_output():
    assert (
        TypedDictFigureProvider()._get_output_figure(Foo)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('a', is_required=True),
                ),
                OutputFieldRM(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('b', is_required=True),
                ),
            ),
        )
    )


def test_non_total_input():
    assert (
        TypedDictFigureProvider()._get_input_figure(Bar)
        ==
        InputFigure(
            constructor=Bar,
            extra=None,
            fields=(
                InputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
                InputFieldRM(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
            ),
        )
    )


def test_non_total_output():
    assert (
        TypedDictFigureProvider()._get_output_figure(Bar)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('a', is_required=False),
                ),
                OutputFieldRM(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('b', is_required=False),
                ),
            ),
        )
    )
