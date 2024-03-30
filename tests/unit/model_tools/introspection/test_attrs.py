import typing
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Tuple
from unittest.mock import ANY

import pytest
from tests_helpers import ATTRS_WITH_ALIAS, requires

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultFactoryWithSelf,
    DefaultValue,
    InputField,
    InputShape,
    IntrospectionError,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    ParamKwargs,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.model_tools.introspection.attrs import get_attrs_shape

pytest.importorskip("attrs")

import attr  # noqa: E402
from attrs import Factory, define, field  # noqa: E402


def int_factory_with_self(x):
    return 0


@define
class NewStyle:
    a: int
    _b: str
    c: str = field(init=False)
    d: int = field(kw_only=True)

    e: int = 1
    f: int = field(default=2)
    g: list = field(factory=list)
    h: str = field(default="", metadata={"meta": "data"})
    i: "int" = field(default=3)
    j: int = field(default=Factory(int_factory_with_self, takes_self=True))


def test_new_style():
    assert (
        get_attrs_shape(NewStyle)
        ==
        Shape(
            input=InputShape(
                constructor=NewStyle,
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
                        id="_b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="d",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="e",
                        default=DefaultValue(1),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="f",
                        default=DefaultValue(2),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=list,
                        id="g",
                        default=DefaultFactory(list),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id="h",
                        default=DefaultValue(""),
                        is_required=False,
                        metadata=MappingProxyType({"meta": "data"}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="i",
                        default=DefaultValue(3),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="j",
                        default=DefaultFactoryWithSelf(int_factory_with_self),
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
                        field_id="_b",
                        name="b",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="e",
                        name="e",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="f",
                        name="f",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="g",
                        name="g",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="h",
                        name="h",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="i",
                        name="i",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="j",
                        name="j",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="d",
                        name="d",
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({"a", "_b", "d", "e", "f", "g", "h", "i", "j"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="_b",
                        default=NoDefault(),
                        accessor=create_attr_accessor("_b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="c",
                        default=NoDefault(),
                        accessor=create_attr_accessor("c", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="d",
                        default=NoDefault(),
                        accessor=create_attr_accessor("d", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="e",
                        default=DefaultValue(1),
                        accessor=create_attr_accessor("e", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="f",
                        default=DefaultValue(2),
                        accessor=create_attr_accessor("f", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=list,
                        id="g",
                        default=DefaultFactory(list),
                        accessor=create_attr_accessor("g", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id="h",
                        default=DefaultValue(""),
                        accessor=create_attr_accessor("h", is_required=True),
                        metadata=MappingProxyType({"meta": "data"}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="i",
                        default=DefaultValue(3),
                        accessor=create_attr_accessor("i", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="j",
                        default=DefaultFactoryWithSelf(int_factory_with_self),
                        accessor=create_attr_accessor("j", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "_b", "c", "d", "e", "f", "g", "h", "i", "j"}),
            ),
        )
    )


@attr.s
class OldStyle:
    a = attr.ib()
    b = attr.ib(type=int)
    c: int


def test_old_style():
    assert (
        get_attrs_shape(OldStyle)
        ==
        Shape(
            input=InputShape(
                constructor=OldStyle,
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
                        type=int,
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
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="b",
                        default=NoDefault(),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
        )
    )


def int_factory():
    return 0


@define
class CustomInit:
    a: int
    b: int = field(factory=int_factory, metadata={"meta": "data"})
    _c: int = field(kw_only=True)
    d: int = 10

    def __init__(self, a: str, b: str, c):
        self.__attrs_init__(int(a), int(b), int(c))


def test_custom_init():
    assert (
        get_attrs_shape(CustomInit)
        ==
        Shape(
            input=InputShape(
                constructor=CustomInit,
                kwargs=None,
                fields=(
                    InputField(
                        type=str,
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
                        metadata=MappingProxyType({"meta": "data"}),
                        original=ANY,
                    ),
                    InputField(
                        type=Any,
                        id="_c",
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
                    Param(
                        field_id="_c",
                        name="c",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "_c"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="b",
                        default=DefaultFactory(int_factory),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({"meta": "data"}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="_c",
                        default=NoDefault(),
                        accessor=create_attr_accessor("_c", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="d",
                        default=DefaultValue(value=10),
                        accessor=create_attr_accessor("d", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "_c", "d"}),
            ),
        )
    )


@define
class CustomInitUnknownParams:
    a: int
    other: dict

    def __init__(self, a: int, b: str, c: bytes):
        self.__attrs_init__(a, {"b": b, "c": c})


def test_custom_init_unknown_params():
    assert (
        get_attrs_shape(CustomInitUnknownParams)
        ==
        Shape(
            input=InputShape(
                constructor=CustomInitUnknownParams,
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
                    InputField(
                        type=bytes,
                        id="c",
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
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=dict,
                        id="other",
                        default=NoDefault(),
                        accessor=create_attr_accessor("other", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "other"}),
            ),
        )
    )


@define
class CustomInitKwargs:
    a: int

    def __init__(self, a: int, **kwargs):
        self.__attrs_init__(a)


@define
class CustomInitKwargsTyped:
    a: int

    def __init__(self, a: int, **kwargs: str):
        self.__attrs_init__(a)


def test_custom_init_kwargs():
    assert (
        get_attrs_shape(CustomInitKwargs)
        ==
        Shape(
            input=InputShape(
                constructor=CustomInitKwargs,
                kwargs=ParamKwargs(Any),
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
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )

    assert (
        get_attrs_shape(CustomInitKwargsTyped)
        ==
        Shape(
            input=InputShape(
                constructor=CustomInitKwargsTyped,
                kwargs=ParamKwargs(str),
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
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )


@define
class NoneAttr:
    a: None


def test_none_attr():
    assert (
        get_attrs_shape(NoneAttr)
        ==
        Shape(
            input=InputShape(
                constructor=NoneAttr,
                kwargs=None,
                fields=(
                    InputField(
                        type=type(None),
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
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=type(None),
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
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
        get_attrs_shape(NoneAttrCustomInit)
        ==
        Shape(
            input=InputShape(
                constructor=NoneAttrCustomInit,
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
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=type(None),
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    @define
    class WithAnnotated:
        a: typing.Annotated[int, "metadata"]

    assert (
        get_attrs_shape(WithAnnotated)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, "metadata"],
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
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=typing.Annotated[int, "metadata"],
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
        )
    )


def test_not_attrs():
    @dataclass
    class IAmDataclass:
        foo: int

    with pytest.raises(IntrospectionError):
        get_attrs_shape(IAmDataclass)

    with pytest.raises(IntrospectionError):
        get_attrs_shape(Tuple[IAmDataclass, int])


def test_inheritance_new_style():
    @define
    class Parent:
        a: int
        b: int

    @define
    class Child(Parent):
        a: int
        c: int

    assert (
        get_attrs_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="c",
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
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "c"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="b",
                        default=NoDefault(),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="c",
                        default=NoDefault(),
                        accessor=create_attr_accessor("c", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "c"}),
            ),
        )
    )


def test_inheritance_old_style():
    @attr.s
    class Parent:
        a = attr.ib(type=int)
        b = attr.ib(type=int)
        d: int

    @attr.s
    class Child(Parent):
        a = attr.ib(type=int)
        c = attr.ib(type=int)
        e: int

    assert (
        get_attrs_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="b",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="c",
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
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"a", "c"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="b",
                        default=NoDefault(),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="c",
                        default=NoDefault(),
                        accessor=create_attr_accessor("c", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "c"}),
            ),
        )
    )


@requires(ATTRS_WITH_ALIAS)
def test_alias_new_style():
    @define
    class WithAliases:
        foo: int = field(alias="foo1")
        _foo: int = field(alias="foo2")

    assert (
        get_attrs_shape(WithAliases)
        ==
        Shape(
            input=InputShape(
                constructor=WithAliases,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="foo",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="_foo",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="foo",
                        name="foo1",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="_foo",
                        name="foo2",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"foo", "_foo"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="foo",
                        default=NoDefault(),
                        accessor=create_attr_accessor("foo", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="_foo",
                        default=NoDefault(),
                        accessor=create_attr_accessor("_foo", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"foo", "_foo"}),
            ),
        )
    )


@requires(ATTRS_WITH_ALIAS)
def test_alias_old_style():
    @attr.s
    class WithAliases:
        foo = attr.ib(type=int, alias="foo1")
        _foo = attr.ib(type=int, alias="foo2")

    assert (
        get_attrs_shape(WithAliases)
        ==
        Shape(
            input=InputShape(
                constructor=WithAliases,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="foo",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id="_foo",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="foo",
                        name="foo1",
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id="_foo",
                        name="foo2",
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({"foo", "_foo"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="foo",
                        default=NoDefault(),
                        accessor=create_attr_accessor("foo", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id="_foo",
                        default=NoDefault(),
                        accessor=create_attr_accessor("_foo", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"foo", "_foo"}),
            ),
        )
    )
