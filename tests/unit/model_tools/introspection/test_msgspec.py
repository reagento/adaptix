from types import MappingProxyType, NoneType
from typing import ClassVar, Union
from unittest.mock import ANY

from msgspec import NODEFAULT, Struct, field
from msgspec.structs import FieldInfo

from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    Inp,
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
         == get_struct_shape(BasicStruct)
    )


