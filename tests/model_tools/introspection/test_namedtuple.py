import typing
from collections import namedtuple
from types import MappingProxyType
from typing import Any, NamedTuple

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools import (
    AttrAccessor,
    DefaultValue,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_named_tuple_figure,
)
from adaptix._internal.model_tools.definitions import Figure
from tests_helpers import requires


def test_order_ab():
    FooAB = namedtuple('FooAB', 'a b')

    assert (
        get_named_tuple_figure(FooAB)
        ==
        Figure(
            input=InputFigure(
                constructor=FooAB,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        name='a',
                        default=NoDefault(),
                        is_required=True,
                        param_kind=ParamKind.POS_OR_KW,
                        metadata=MappingProxyType({}),
                        param_name='a',
                    ),
                    InputField(
                        type=Any,
                        name='b',
                        default=NoDefault(),
                        is_required=True,
                        param_kind=ParamKind.POS_OR_KW,
                        metadata=MappingProxyType({}),
                        param_name='b',
                    ),
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=OutputFigure(
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
                overriden_types=frozenset({'a', 'b'}),
            )
        )
    )


def test_order_ba():
    FooBA = namedtuple('FooBA', 'b a')

    assert (
        get_named_tuple_figure(FooBA)
        ==
        Figure(
            input=InputFigure(
                constructor=FooBA,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        name='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
                    ),
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
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=OutputFigure(
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
                overriden_types=frozenset({'a', 'b'}),
            ),
        )
    )


def func():
    return 0


def test_defaults():
    FooDefs = namedtuple('FooDefs', 'a b c', defaults=[0, func])

    assert (
        get_named_tuple_figure(FooDefs)
        ==
        Figure(
            input=InputFigure(
                constructor=FooDefs,
                kwargs=None,
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
                        type=Any,
                        name='b',
                        default=DefaultValue(0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
                    ),
                    InputField(
                        type=Any,
                        name='c',
                        default=DefaultValue(func),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='c',
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
            output=OutputFigure(
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
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
        )
    )


def test_rename():
    WithRename = namedtuple('WithRename', ['abc', 'def', 'ghi', 'abc'], defaults=[0], rename=True)

    assert (
        get_named_tuple_figure(WithRename)
        ==
        Figure(
            input=InputFigure(
                constructor=WithRename,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        name='abc',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='abc',
                    ),
                    InputField(
                        type=Any,
                        name='_1',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='_1',
                    ),
                    InputField(
                        type=Any,
                        name='ghi',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='ghi',
                    ),
                    InputField(
                        type=Any,
                        name='_3',
                        default=DefaultValue(0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='_3',
                    ),
                ),
                overriden_types=frozenset({'abc', '_1', 'ghi', '_3'}),
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=Any,
                        name='abc',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('abc', is_required=True),
                    ),
                    OutputField(
                        type=Any,
                        name='_1',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('_1', is_required=True),
                    ),
                    OutputField(
                        type=Any,
                        name='ghi',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('ghi', is_required=True),
                    ),
                    OutputField(
                        type=Any,
                        name='_3',
                        default=DefaultValue(0),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('_3', is_required=True),
                    ),
                ),
                overriden_types=frozenset({'abc', '_1', 'ghi', '_3'}),
            ),
        )
    )


def test_class_hinted_namedtuple():
    BarA = NamedTuple('BarA', a=int, b=str)

    assert (
        get_named_tuple_figure(BarA)
        ==
        Figure(
            input=InputFigure(
                constructor=BarA,
                kwargs=None,
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
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=OutputFigure(
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
                overriden_types=frozenset({'a', 'b'}),
            )
        )

    )


def test_hinted_namedtuple():
    # ClassVar is not supported in NamedTuple

    class BarB(NamedTuple):
        a: int
        b: str = 'abc'
        c: 'bool' = False

    assert (
        get_named_tuple_figure(BarB)
        ==
        Figure(
            input=InputFigure(
                constructor=BarB,
                kwargs=None,
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
                        default=DefaultValue('abc'),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
                    ),
                    InputField(
                        type=bool,
                        name='c',
                        default=DefaultValue(False),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='c',
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
            output=OutputFigure(
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
                    OutputField(
                        type=bool,
                        name='c',
                        default=DefaultValue(False),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('c', is_required=True),
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
        )
    )



def test_inheritance():
    class Parent(NamedTuple):
        a: int

    class Child(Parent):
        b: str

    assert (
        get_named_tuple_figure(Child)
        ==
        Figure(
            input=InputFigure(
                constructor=Child,
                kwargs=None,
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
                overriden_types=frozenset(),
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=int,
                        name='a',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('a', is_required=True),
                    ),
                ),
                overriden_types=frozenset(),
            ),
        )
    )


def test_inheritance_overriden_types():
    class Parent(NamedTuple):
        a: int
        b: str

    class Child(Parent):
        a: bool
        c: str

    assert (
        get_named_tuple_figure(Child)
        ==
        Figure(
            input=InputFigure(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=bool,
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
                ),
                overriden_types=frozenset({'a'}),
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=bool,
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
                overriden_types=frozenset({'a'}),
            ),
        )
    )


def test_inheritance_overriden_types_functional_parent():
    Parent = namedtuple('Parent', 'a b')

    class Child(Parent):
        a: bool
        c: str

    assert (
        get_named_tuple_figure(Child)
        ==
        Figure(
            input=InputFigure(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=bool,
                        name='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='a',
                    ),
                    InputField(
                        type=Any,
                        name='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
                    ),
                ),
                overriden_types=frozenset({'a'}),
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=bool,
                        name='a',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('a', is_required=True),
                    ),
                    OutputField(
                        type=Any,
                        name='b',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=AttrAccessor('b', is_required=True),
                    ),
                ),
                overriden_types=frozenset({'a'}),
            ),
        )
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    class WithAnnotated(NamedTuple):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_named_tuple_figure(WithAnnotated)
        ==
        Figure(
            input=InputFigure(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        name='annotated_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='annotated_field',
                    ),
                ),
                overriden_types=frozenset({'annotated_field'}),
            ),
            output=OutputFigure(
                fields=(
                    OutputField(
                        type=typing.Annotated[int, 'metadata'],
                        name='annotated_field',
                        default=NoDefault(),
                        accessor=AttrAccessor('annotated_field', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                ),
                overriden_types=frozenset({'annotated_field'}),
            ),
        )
    )
