from types import MappingProxyType, NoneType
from typing import Annotated, Any, ClassVar, Sequence, Union
from unittest.mock import ANY

from msgspec import Struct, field

from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.model_tools.introspection.msgspec import get_struct_shape


def none_factory() -> None:
    return None


class BasicStruct(Struct):
    a: str
    g: ClassVar[str]
    c: bool = field(default=True)
    b: Union[str, int] = 3
    d: None = field(default_factory=none_factory)
    e: ClassVar[float] = 4.1
    f: float = float("-inf")

    def __post_init__(self):
        pass


def test_basic():
    assert (
        get_struct_shape(BasicStruct)
        ==
        Shape(
            input=InputShape(
                constructor=BasicStruct,
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
                        type=bool,
                        id="c",
                        default=DefaultValue(True),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=Union[str, int],
                        id="b",
                        default=DefaultValue(3),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=NoneType,
                        id="d",
                        default=DefaultFactory(none_factory),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=float,
                        id="f",
                        default=DefaultValue(float("-inf")),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="d",
                        name="d",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="f",
                        name="f",
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c", "d", "f"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=str,
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=bool,
                        id="c",
                        default=DefaultValue(True),
                        accessor=create_attr_accessor("c", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=Union[str, int],
                        id="b",
                        default=DefaultValue(3),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=NoneType,
                        id="d",
                        default=DefaultFactory(none_factory),
                        accessor=create_attr_accessor("d", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=float,
                        id="f",
                        default=DefaultValue(float("-inf")),
                        accessor=create_attr_accessor("f", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b", "c", "d", "f"}),
            ),
        )
    )


class BarParent(Struct):
    a: Sequence[int]
    b: float


class BarChild(BarParent):
    c: int
    a: list[int]


def test_inheritance():
    assert (
        get_struct_shape(BarChild)
        ==
        Shape(
            InputShape(
                constructor=BarChild,
                kwargs=None,
                fields=(
                    InputField(
                        type=list[int],
                        id="a",
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=float,
                        id="b",
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
                        field_id="a",
                        name="a",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="c",
                        name="c",
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({"a", "c"}),
            ),
            OutputShape(
                fields=(
                    OutputField(
                        type=list[int],
                        id="a",
                        default=NoDefault(),
                        accessor=create_attr_accessor("a", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=float,
                        id="b",
                        default=NoDefault(),
                        accessor=create_attr_accessor("b", is_required=True),
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


class ForwardRefStruct(Struct):
    a: "int"


class ForwardRefStructChild(ForwardRefStruct):
    b: str

def test_forward_ref():
    assert (
        get_struct_shape(ForwardRefStruct)
        ==
        Shape(
            input=InputShape(
                constructor=ForwardRefStruct,
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
                        kind=ParamKind.KW_ONLY,
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

class WithAnnotatedField(Struct):
    a: Annotated[int, "metadata"]

def test_annotated():
    assert (
        get_struct_shape(WithAnnotatedField)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotatedField,
                kwargs=None,
                fields=(
                    InputField(
                        type=Annotated[int, "metadata"],
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
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({"a"}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=Annotated[int, "metadata"],
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


class UsingFeatures(
    Struct,
    kw_only=True,
    eq=False,
    frozen=True,
    tag=True,
    omit_defaults=True,
    forbid_unknown_fields=True,
    array_like=True,
):
    a: int = field(name="g")
    b: bool = True

def test_features():
    assert (
        get_struct_shape(UsingFeatures)
        ==
        Shape(
            InputShape(
                constructor=UsingFeatures,
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
                        type=bool,
                        id="b",
                        default=DefaultValue(True),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id="a",
                        name="a",
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id="b",
                        name="b",
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
            OutputShape(
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
                        type=bool,
                        id="b",
                        default=DefaultValue(True),
                        accessor=create_attr_accessor("b", is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({"a", "b"}),
            ),
        )
    )
