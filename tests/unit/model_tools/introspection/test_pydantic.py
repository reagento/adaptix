from functools import cached_property
from typing import Any
from unittest.mock import ANY

import pytest
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field
from pydantic.fields import ModelPrivateAttr
from pydantic_core import PydanticUndefined
from tests_helpers import raises_exc, requires

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools.definitions import (
    ClarifiedIntrospectionError,
    DefaultFactory,
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    ParamKwargs,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.model_tools.introspection.pydantic import get_pydantic_shape


def test_basic():
    class MyModel(BaseModel):
        a: str
        b: str = Field()
        c: str = "foo"
        d: str = Field("foo")
        e: list = Field(default_factory=list)

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
            fields=(
                InputField(
                    id="a",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
                InputField(id="b", type=str, default=NoDefault(), metadata={}, original=ANY, is_required=True),
                InputField(
                    id="c",
                    type=str,
                    default=DefaultValue(value="foo"),
                    metadata={},
                    original=ANY,
                    is_required=False,
                ),
                InputField(
                    id="d",
                    type=str,
                    default=DefaultValue(value="foo"),
                    metadata={},
                    original=ANY,
                    is_required=False,
                ),
                InputField(
                    id="e",
                    type=list,
                    default=DefaultFactory(factory=list),
                    metadata={},
                    original=ANY,
                    is_required=False,
                ),
            ),
            overriden_types=frozenset({"c", "e", "d", "a", "b"}),
            params=(
                Param(field_id="a", name="a", kind=ParamKind.KW_ONLY),
                Param(field_id="b", name="b", kind=ParamKind.KW_ONLY),
                Param(field_id="c", name="c", kind=ParamKind.KW_ONLY),
                Param(field_id="d", name="d", kind=ParamKind.KW_ONLY),
                Param(field_id="e", name="e", kind=ParamKind.KW_ONLY),
            ),
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="a", is_required=True),
                ),
                OutputField(
                    id="b",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="b", is_required=True),
                ),
                OutputField(
                    id="c",
                    type=str,
                    default=DefaultValue(value="foo"),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="c", is_required=True),
                ),
                OutputField(
                    id="d",
                    type=str,
                    default=DefaultValue(value="foo"),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="d", is_required=True),
                ),
                OutputField(
                    id="e",
                    type=list,
                    default=DefaultFactory(factory=list),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="e", is_required=True),
                ),
            ),
            overriden_types=frozenset({"c", "e", "d", "a", "b"}),
        ),
    )


def test_fields_with_ellipsis_default():
    class MyModel(BaseModel):
        a: int
        b: int = ...
        c: int = Field(...)

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
                InputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
                InputField(
                    id="c",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
            ),
            overriden_types=frozenset({"a", "b", "c"}),
            params=(
                Param(field_id="a", name="a", kind=ParamKind.KW_ONLY),
                Param(field_id="b", name="b", kind=ParamKind.KW_ONLY),
                Param(field_id="c", name="c", kind=ParamKind.KW_ONLY),
            ),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="a", is_required=True),
                ),
                OutputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="b", is_required=True),
                ),
                OutputField(
                    id="c",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="c", is_required=True),
                ),
            ),
            overriden_types=frozenset({"a", "b", "c"}),
        ),
    )


def test_private_attrs():
    class MyModel(BaseModel):
        a: str
        _b: int
        _c: int = PrivateAttr()
        _d: int = 1
        _e: int = PrivateAttr(2)
        _f: list = PrivateAttr(default_factory=list)
        _g = PrivateAttr(default_factory=list)

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id="a",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
            ),
            overriden_types=frozenset({"a"}),
            params=(Param(field_id="a", name="a", kind=ParamKind.KW_ONLY),),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="a", is_required=True),
                ),
                OutputField(
                    id="_c",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(),
                    accessor=create_attr_accessor(attr_name="_c", is_required=True),
                ),
                OutputField(
                    id="_d",
                    type=int,
                    default=DefaultValue(value=1),
                    metadata={},
                    original=ModelPrivateAttr(default=1),
                    accessor=create_attr_accessor(attr_name="_d", is_required=True),
                ),
                OutputField(
                    id="_e",
                    type=int,
                    default=DefaultValue(value=2),
                    metadata={},
                    original=ModelPrivateAttr(default=2),
                    accessor=create_attr_accessor(attr_name="_e", is_required=True),
                ),
                OutputField(
                    id="_f",
                    type=list,
                    default=DefaultFactory(factory=list),
                    metadata={},
                    original=ModelPrivateAttr(default_factory=list),
                    accessor=create_attr_accessor(attr_name="_f", is_required=True),
                ),
                OutputField(
                    id="_g",
                    type=Any,
                    default=DefaultFactory(factory=list),
                    metadata={},
                    original=ModelPrivateAttr(default_factory=list),
                    accessor=create_attr_accessor(attr_name="_g", is_required=True),
                ),
                OutputField(
                    id="_b",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(),
                    accessor=create_attr_accessor(attr_name="_b", is_required=True),
                ),
            ),
            overriden_types=frozenset({"_b", "_c", "_d", "_e", "_f", "a", "_g"}),
        ),
    )


def test_computed_fields():
    class MyModel(BaseModel):
        a: str
        _b: int

        @computed_field
        @property
        def simple(self) -> int:
            return 1

        @computed_field
        def simple_no_prop(self) -> int:
            return 1

        @computed_field
        @cached_property
        def simple_cached_prop(self) -> int:
            return 1

        @computed_field
        @property
        def _private(self) -> int:
            return 1

        @computed_field(return_type=str)
        @property
        def override_return_type(self) -> int:
            return 1

        @computed_field(return_type=str)
        @property
        def no_type_return_type(self):
            return 1

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(InputField(id="a", type=str, default=NoDefault(), metadata={}, original=ANY, is_required=True),),
            overriden_types=frozenset({"a"}),
            params=(Param(field_id="a", name="a", kind=ParamKind.KW_ONLY),),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="a", is_required=True),
                ),
                OutputField(
                    id="simple",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="simple", is_required=True),
                ),
                OutputField(
                    id="simple_no_prop",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="simple_no_prop", is_required=True),
                ),
                OutputField(
                    id="simple_cached_prop",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="simple_cached_prop", is_required=True),
                ),
                OutputField(
                    id="_private",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="_private", is_required=True),
                ),
                OutputField(
                    id="override_return_type",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="override_return_type", is_required=True),
                ),
                OutputField(
                    id="no_type_return_type",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="no_type_return_type", is_required=True),
                ),
                OutputField(
                    id="_b",
                    type=int,
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(default=PydanticUndefined),
                    accessor=create_attr_accessor(attr_name="_b", is_required=True),
                ),
            ),
            overriden_types=frozenset(
                {
                    "_b",
                    "_private",
                    "a",
                    "no_type_return_type",
                    "simple",
                    "simple_cached_prop",
                    "simple_no_prop",
                    "override_return_type",
                },
            ),
        ),
    )


def test_order():
    class MyModel(BaseModel):
        f1: str

        @computed_field
        @property
        def f2(self) -> str:
            return ""

        _f3: str

        f4: str

        @computed_field
        @property
        def f5(self) -> str:
            return ""

        _f6: str

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id="f1",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
                InputField(
                    id="f4",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
            ),
            overriden_types=frozenset({"f1", "f4"}),
            params=(
                Param(field_id="f1", name="f1", kind=ParamKind.KW_ONLY),
                Param(field_id="f4", name="f4", kind=ParamKind.KW_ONLY),
            ),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="f1",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f1", is_required=True),
                ),
                OutputField(
                    id="f4",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f4", is_required=True),
                ),
                OutputField(
                    id="f2",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f2", is_required=True),
                ),
                OutputField(
                    id="f5",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f5", is_required=True),
                ),
                OutputField(
                    id="_f3",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(),
                    accessor=create_attr_accessor(attr_name="_f3", is_required=True),
                ),
                OutputField(
                    id="_f6",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(),
                    accessor=create_attr_accessor(attr_name="_f6", is_required=True),
                ),
            ),
            overriden_types=frozenset({"_f3", "_f6", "f1", "f2", "f4", "f5"}),
        ),
    )


@pytest.mark.parametrize(
    ["extra", "param_kwargs"],
    [
        ("allow", ParamKwargs(Any)),
        ("ignore", ParamKwargs(Any)),
        ("forbid", None),
    ],
)
def test_kwargs(extra, param_kwargs):
    class MyModel(BaseModel):
        f1: str

        model_config = ConfigDict(extra=extra)

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id="f1",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
            ),
            overriden_types=frozenset({"f1"}),
            params=(Param(field_id="f1", name="f1", kind=ParamKind.KW_ONLY),),
            kwargs=param_kwargs,
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="f1",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f1", is_required=True),
                ),
            ),
            overriden_types=frozenset({"f1"}),
        ),
    )


def test_allowed_custom_init():
    class MyModel(BaseModel):
        f1: str

        def __init__(self, **kwargs):
            super().__init__(self, **kwargs)

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(InputField(id="f1", type=str, default=NoDefault(), metadata={}, original=ANY, is_required=True),),
            overriden_types=frozenset({"f1"}),
            params=(Param(field_id="f1", name="f1", kind=ParamKind.KW_ONLY),),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="f1",
                    type=str,
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f1", is_required=True),
                ),
            ),
            overriden_types=frozenset({"f1"}),
        ),
    )


def test_forbidden_custom_init():
    class MyModel(BaseModel):
        f1: str

        def __init__(self, f1: int):
            super().__init__(self, f1=str(f1))

    raises_exc(
        ClarifiedIntrospectionError(
            "Pydantic model `__init__` must takes only self and one variable keyword parameter",
        ),
        lambda: get_pydantic_shape(MyModel),
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    from typing import Annotated

    class MyModel(BaseModel):
        f1: Annotated[str, "meta"]

        @computed_field
        @property
        def f2(self) -> Annotated[str, "meta"]:
            return ""

        @computed_field(return_type=Annotated[str, "meta"])
        @property
        def f3(self) -> str:
            return ""

        _f4: Annotated[str, "meta"]

    assert get_pydantic_shape(MyModel) == Shape(
        input=InputShape(
            fields=(
                InputField(
                    id="f1",
                    type=Annotated[str, "meta"],
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    is_required=True,
                ),
            ),
            overriden_types=frozenset({"f1"}),
            params=(Param(field_id="f1", name="f1", kind=ParamKind.KW_ONLY),),
            kwargs=ParamKwargs(type=Any),
            constructor=MyModel,
        ),
        output=OutputShape(
            fields=(
                OutputField(
                    id="f1",
                    type=Annotated[str, "meta"],
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f1", is_required=True),
                ),
                OutputField(
                    id="f2",
                    type=Annotated[str, "meta"],
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f2", is_required=True),
                ),
                OutputField(
                    id="f3",
                    type=Annotated[str, "meta"],
                    default=NoDefault(),
                    metadata={},
                    original=ANY,
                    accessor=create_attr_accessor(attr_name="f3", is_required=True),
                ),
                OutputField(
                    id="_f4",
                    type=Annotated[str, "meta"],
                    default=NoDefault(),
                    metadata={},
                    original=ModelPrivateAttr(),
                    accessor=create_attr_accessor(attr_name="_f4", is_required=True),
                ),
            ),
            overriden_types=frozenset({"f3", "_f4", "f1", "f2"}),
        ),
    )
