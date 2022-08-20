import typing
from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.feature_requirement import HAS_PY_39
from dataclass_factory_30.model_tools import (
    InputField,
    InputFigure,
    ItemAccessor,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_typed_dict_input_figure,
    get_typed_dict_output_figure,
)
from tests_helpers import requires_annotated


class Foo(TypedDict, total=True):
    a: int
    b: str
    c: 'bool'


class Bar(TypedDict, total=False):
    a: int
    b: str
    c: 'bool'


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
                    param_name='a',
                ),
                InputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='b',
                ),
                InputField(
                    type=bool,
                    name='c',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='c',
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
                OutputField(
                    type=bool,
                    name='c',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('c', is_required=True),
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
                    param_name='a',
                ),
                InputField(
                    type=str,
                    name='b',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='b',
                ),
                InputField(
                    type=bool,
                    name='c',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='c',
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
                OutputField(
                    type=bool,
                    name='c',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('c', is_required=False),
                ),
            ),
        )
    )


class ParentNotTotal(TypedDict, total=False):
    x: int


class ChildTotal(ParentNotTotal, total=True):
    y: str


class GrandChildNotTotal(ChildTotal, total=False):
    z: str


def _maybe_repl(value: bool, *, to: bool) -> bool:
    return value if HAS_PY_39 else to


def test_inheritance_first():
    assert (
        get_typed_dict_input_figure(ParentNotTotal)
        ==
        InputFigure(
            constructor=ParentNotTotal,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='x',
                ),
            ),
        )
    )
    assert (
        get_typed_dict_output_figure(ParentNotTotal)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('x', is_required=False),
                ),
            ),
        )
    )


def test_inheritance_second():
    assert (
        get_typed_dict_input_figure(ChildTotal)
        ==
        InputFigure(
            constructor=ChildTotal,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    is_required=_maybe_repl(False, to=True),
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='x',
                ),
                InputField(
                    type=str,
                    name='y',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='y',
                ),
            ),
        )
    )
    assert (
        get_typed_dict_output_figure(ChildTotal)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('x', is_required=_maybe_repl(False, to=True)),
                ),
                OutputField(
                    type=str,
                    name='y',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('y', is_required=True),
                ),
            ),
        )
    )


def test_inheritance_third():
    assert (
        get_typed_dict_input_figure(GrandChildNotTotal)
        ==
        InputFigure(
            constructor=GrandChildNotTotal,
            extra=None,
            fields=(
                InputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='x',
                ),
                InputField(
                    type=str,
                    name='y',
                    default=NoDefault(),
                    is_required=_maybe_repl(True, to=False),
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='y',
                ),
                InputField(
                    type=str,
                    name='z',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='z',
                ),
            ),
        )
    )
    assert (
        get_typed_dict_output_figure(GrandChildNotTotal)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='x',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('x', is_required=False),
                ),
                OutputField(
                    type=str,
                    name='y',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('y', is_required=_maybe_repl(True, to=False)),
                ),
                OutputField(
                    type=str,
                    name='z',
                    default=NoDefault(),
                    metadata=MappingProxyType({}),
                    accessor=ItemAccessor('z', is_required=False),
                ),
            ),
        )
    )


@requires_annotated
def test_annotated():
    class WithAnnotatedTotal(TypedDict):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_input_figure(WithAnnotatedTotal)
        ==
        InputFigure(
            constructor=WithAnnotatedTotal,
            extra=None,
            fields=(
                InputField(
                    type=typing.Annotated[int, 'metadata'],
                    name='annotated_field',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='annotated_field',
                ),
            ),
        )
    )

    assert (
        get_typed_dict_output_figure(WithAnnotatedTotal)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=typing.Annotated[int, 'metadata'],
                    name='annotated_field',
                    default=NoDefault(),
                    accessor=ItemAccessor('annotated_field', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )

    class WithAnnotatedNotTotal(TypedDict, total=False):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_input_figure(WithAnnotatedNotTotal)
        ==
        InputFigure(
            constructor=WithAnnotatedNotTotal,
            extra=None,
            fields=(
                InputField(
                    type=typing.Annotated[int, 'metadata'],
                    name='annotated_field',
                    default=NoDefault(),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                    param_name='annotated_field',
                ),
            ),
        )
    )

    assert (
        get_typed_dict_output_figure(WithAnnotatedNotTotal)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=typing.Annotated[int, 'metadata'],
                    name='annotated_field',
                    default=NoDefault(),
                    accessor=ItemAccessor('annotated_field', is_required=False),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )
