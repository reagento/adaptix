# ruff: noqa: PYI024, UP014, FBT003
from collections import namedtuple
from types import MappingProxyType
from typing import Annotated, Any, NamedTuple
from unittest.mock import ANY

from adaptix._internal.model_tools.definitions import (
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_key_accessor,
)
from adaptix._internal.model_tools.introspection.named_tuple import get_named_tuple_shape


def test_order_ab():
    FooAB = namedtuple("FooAB", "a b")

    assert (
        get_named_tuple_shape(FooAB)
        ==
        Shape(
            input=InputShape(
                constructor=FooAB,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        accessor=create_key_accessor(0, access_error=None),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        accessor=create_key_accessor(1, access_error=None),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
        )
    )


def test_order_ba():
    FooBA = namedtuple("FooBA", "b a")

    assert (
        get_named_tuple_shape(FooBA)
        ==
        Shape(
            input=InputShape(
                constructor=FooBA,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
        )
    )


def func():
    return 0


def test_defaults():
    FooDefs = namedtuple("FooDefs", "a b c", defaults=[0, func])

    assert (
        get_named_tuple_shape(FooDefs)
        ==
        Shape(
            input=InputShape(
                constructor=FooDefs,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="b",
                        default=DefaultValue(0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="c",
                        default=DefaultValue(func),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Any,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="b",
                        default=DefaultValue(0),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="c",
                        default=DefaultValue(func),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(2, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c"}),
            ),
        )
    )


def test_rename():
    WithRename = namedtuple("WithRename", ["abc", "def", "ghi", "abc"], defaults=[0], rename=True)

    assert (
        get_named_tuple_shape(WithRename)
        ==
        Shape(
            input=InputShape(
                constructor=WithRename,
                kwargs=None,
                fields=(
                    InputField(
                        type=Any,
                        id="abc",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="_1",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="ghi",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="_3",
                        default=DefaultValue(0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="abc",
                        name="abc",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="_1",
                        name="_1",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="ghi",
                        name="ghi",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="_3",
                        name="_3",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"abc", "_1", "ghi", "_3"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Any,
                        id="abc",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="_1",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="ghi",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(2, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="_3",
                        default=DefaultValue(0),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(3, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"abc", "_1", "ghi", "_3"}),
            ),
        )
    )


def test_class_hinted_namedtuple():
    BarA = NamedTuple("BarA", a=int, b=str)

    assert (
        get_named_tuple_shape(BarA)
        ==
        Shape(
            input=InputShape(
                constructor=BarA,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="b",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
        )

    )


def test_hinted_namedtuple():
    # ClassVar is not supported in NamedTuple

    class BarB(NamedTuple):
        a: int
        b: str = "abc"
        c: "bool" = False

    assert (
        get_named_tuple_shape(BarB)
        ==
        Shape(
            input=InputShape(
                constructor=BarB,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id="b",
                        default=DefaultValue("abc"),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=bool,
                        id="c",
                        default=DefaultValue(False),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="b",
                        default=DefaultValue("abc"),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=bool,
                        id="c",
                        default=DefaultValue(False),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(2, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c"}),
            ),
        )
    )


def test_inheritance():
    class Parent(NamedTuple):
        a: int

    class Child(Parent):
        b: str

    assert (
        get_named_tuple_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset(),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
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
        get_named_tuple_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=bool,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=bool,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="b",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )


def test_inheritance_overriden_types_functional_parent():
    Parent = namedtuple("Parent", "a b")

    class Child(Parent):
        a: bool
        c: str

    assert (
        get_named_tuple_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=bool,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=bool,
                        id="a",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(0, access_error=None),
                        original=ANY,
                    ),
                    OutputField(
                        type=Any,
                        id="b",
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor(1, access_error=None),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )


def test_annotated():
    class WithAnnotated(NamedTuple):
        annotated_field: Annotated[int, "metadata"]

    assert (
        get_named_tuple_shape(WithAnnotated)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=Annotated[int, "metadata"],
                        id="annotated_field",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="annotated_field",
                        name="annotated_field",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"annotated_field"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Annotated[int, "metadata"],
                        id="annotated_field",
                        default=NoDefault(),
                        accessor=create_key_accessor(0, access_error=None),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"annotated_field"}),
            ),
        )
    )
