import typing
from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.feature_requirement import HAS_ANNOTATED, HAS_PY_39
from dataclass_factory_30.model_tools import (
    InputField,
    InputFigure,
    ItemAccessor,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_typed_dict_figure,
)
from dataclass_factory_30.model_tools.definitions import Figure
from tests_helpers import requires


class Foo(TypedDict, total=True):
    a: int
    b: str
    c: 'bool'


class Bar(TypedDict, total=False):
    a: int
    b: str
    c: 'bool'


def test_total():
    assert (
        get_typed_dict_figure(Foo)
        ==
        Figure(
            input=InputFigure(
                constructor=Foo,
                kwargs=None,
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
            ),
            output=OutputFigure(
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
            ),
        )
    )


def test_non_total():
    assert (
        get_typed_dict_figure(Bar)
        ==
        Figure(
            input=InputFigure(
                constructor=Bar,
                kwargs=None,
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
            ),
            output=OutputFigure(
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
            ),
        )
    )


class ParentNotTotal(TypedDict, total=False):
    x: int


class ChildTotal(ParentNotTotal, total=True):
    y: str


class GrandChildNotTotal(ChildTotal, total=False):
    z: str


def _negate_if_not_py39(value: bool) -> bool:
    return value if HAS_PY_39 else not value


def test_inheritance_first():
    assert (
        get_typed_dict_figure(ParentNotTotal)
        ==
        Figure(
            input=InputFigure(
                constructor=ParentNotTotal,
                kwargs=None,
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
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=int,
                        name='x',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=ItemAccessor('x', is_required=False),
                    ),
                ),
            ),
        )
    )


def test_inheritance_second():
    assert (
        get_typed_dict_figure(ChildTotal)
        ==
        Figure(
            input=InputFigure(
                constructor=ChildTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        name='x',
                        default=NoDefault(),
                        is_required=_negate_if_not_py39(False),
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
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=int,
                        name='x',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=ItemAccessor('x', is_required=_negate_if_not_py39(False)),
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
    )


def test_inheritance_third():
    assert (
        get_typed_dict_figure(GrandChildNotTotal)
        ==
        Figure(
            input=InputFigure(
                constructor=GrandChildNotTotal,
                kwargs=None,
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
                        is_required=_negate_if_not_py39(True),
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
            ),
            output=OutputFigure(
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
                        accessor=ItemAccessor('y', is_required=_negate_if_not_py39(True)),
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
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    class WithAnnotatedTotal(TypedDict):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_figure(WithAnnotatedTotal)
        ==
        Figure(
            input=InputFigure(
                constructor=WithAnnotatedTotal,
                kwargs=None,
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
            ),
            output=OutputFigure(
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
    )

    class WithAnnotatedNotTotal(TypedDict, total=False):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_figure(WithAnnotatedNotTotal)
        ==
        Figure(
            input=InputFigure(
                constructor=WithAnnotatedNotTotal,
                kwargs=None,
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
            ),
            output=OutputFigure(
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
    )
