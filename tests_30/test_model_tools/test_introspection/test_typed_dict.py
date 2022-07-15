from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.model_tools import (
    InputField,
    InputFigure,
    ItemAccessor,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_typed_dict_input_figure,
    get_typed_dict_output_figure
)


class Foo(TypedDict, total=True):
    a: int
    b: str


class Bar(TypedDict, total=False):
    a: int
    b: str


def test_total_input():
    assert (
        get_typed_dict_input_figure(Foo)
        ==
        InputFigure(
            constructor=Foo,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
                InputField(
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
        get_typed_dict_output_figure(Foo)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('a', is_required=True),
                ),
                OutputField(
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
        get_typed_dict_input_figure(Bar)
        ==
        InputFigure(
            constructor=Bar,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                ),
                InputField(
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
        get_typed_dict_output_figure(Bar)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('a', is_required=False),
                ),
                OutputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('b', is_required=False),
                ),
            ),
        )
    )
