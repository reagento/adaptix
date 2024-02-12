import typing
from types import MappingProxyType
from typing import TypedDict

from tests_helpers import requires

from adaptix._internal.feature_requirement import HAS_ANNOTATED, HAS_PY_39, HAS_TYPED_DICT_REQUIRED
from adaptix._internal.model_tools.definitions import (
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
from adaptix._internal.model_tools.introspection.typed_dict import get_typed_dict_shape


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
        get_typed_dict_shape(Foo)
        ==
        Shape(
            input=InputShape(
                constructor=Foo,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=str,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=bool,
                        id='c',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='c',
                        name='c',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('a', access_error=None),
                        original=None,
                    ),
                    OutputField(
                        type=str,
                        id='b',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('b', access_error=None),
                        original=None,
                    ),
                    OutputField(
                        type=bool,
                        id='c',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('c', access_error=None),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
        )
    )


def test_non_total():
    assert (
        get_typed_dict_shape(Bar)
        ==
        Shape(
            input=InputShape(
                constructor=Bar,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=str,
                        id='b',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=bool,
                        id='c',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='c',
                        name='c',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('a', access_error=KeyError),
                        original=None,
                    ),
                    OutputField(
                        type=str,
                        id='b',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('b', access_error=KeyError),
                        original=None,
                    ),
                    OutputField(
                        type=bool,
                        id='c',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('c', access_error=KeyError),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
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
        get_typed_dict_shape(ParentNotTotal)
        ==
        Shape(
            input=InputShape(
                constructor=ParentNotTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='x',
                        name='x',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('x', access_error=KeyError),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
        )
    )


def test_inheritance_second():
    assert (
        get_typed_dict_shape(ChildTotal)
        ==
        Shape(
            input=InputShape(
                constructor=ChildTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        is_required=_negate_if_not_py39(False),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=str,
                        id='y',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='x',
                        name='x',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='y',
                        name='y',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('x', access_error=KeyError if HAS_PY_39 else None),
                        original=None,
                    ),
                    OutputField(
                        type=str,
                        id='y',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('y', access_error=None),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )


def test_inheritance_third():
    assert (
        get_typed_dict_shape(GrandChildNotTotal)
        ==
        Shape(
            input=InputShape(
                constructor=GrandChildNotTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=str,
                        id='y',
                        default=NoDefault(),
                        is_required=_negate_if_not_py39(True),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=str,
                        id='z',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='x',
                        name='x',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='y',
                        name='y',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='z',
                        name='z',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='x',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('x', access_error=KeyError),
                        original=None,
                    ),
                    OutputField(
                        type=str,
                        id='y',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('y', access_error=None if HAS_PY_39 else KeyError),
                        original=None,
                    ),
                    OutputField(
                        type=str,
                        id='z',
                        default=NoDefault(),
                        metadata=MappingProxyType({}),
                        accessor=create_key_accessor('z', access_error=KeyError),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    class WithAnnotatedTotal(TypedDict):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_shape(WithAnnotatedTotal)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotatedTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='annotated_field',
                        name='annotated_field',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        accessor=create_key_accessor('annotated_field', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )

    class WithAnnotatedNotTotal(TypedDict, total=False):
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_typed_dict_shape(WithAnnotatedNotTotal)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotatedNotTotal,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='annotated_field',
                        name='annotated_field',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        accessor=create_key_accessor('annotated_field', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )


@requires(HAS_TYPED_DICT_REQUIRED)
def test_required():
    class Base(TypedDict):
        f1: int
        f2: typing.Required[int]
        f3: typing.NotRequired[int]

    class Child(Base, total=False):
        f4: int
        f5: typing.Required[int]
        f6: typing.NotRequired[int]

    assert (
        get_typed_dict_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='f1',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.Required[int],
                        id='f2',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.NotRequired[int],
                        id='f3',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=int,
                        id='f4',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.Required[int],
                        id='f5',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.NotRequired[int],
                        id='f6',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='f1',
                        name='f1',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f2',
                        name='f2',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f3',
                        name='f3',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f4',
                        name='f4',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f5',
                        name='f5',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f6',
                        name='f6',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='f1',
                        default=NoDefault(),
                        accessor=create_key_accessor('f1', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.Required[int],
                        id='f2',
                        default=NoDefault(),
                        accessor=create_key_accessor('f2', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.NotRequired[int],
                        id='f3',
                        default=NoDefault(),
                        accessor=create_key_accessor('f3', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=int,
                        id='f4',
                        default=NoDefault(),
                        accessor=create_key_accessor('f4', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.Required[int],
                        id='f5',
                        default=NoDefault(),
                        accessor=create_key_accessor('f5', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.NotRequired[int],
                        id='f6',
                        default=NoDefault(),
                        accessor=create_key_accessor('f6', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )


@requires(HAS_TYPED_DICT_REQUIRED)
def test_required_annotated():
    class Base(TypedDict):
        f1: int
        f2: typing.Annotated[typing.Required[int], "metadata"]
        f3: typing.NotRequired[typing.Annotated[int, "metadata"]]

    class Child(Base, total=False):
        f4: int
        f5: typing.Annotated[typing.Required[int], "metadata"]
        f6: typing.NotRequired[typing.Annotated[int, "metadata"]]

    assert (
        get_typed_dict_shape(Child)
        ==
        Shape(
            input=InputShape(
                constructor=Child,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='f1',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.Annotated[typing.Required[int], "metadata"],
                        id='f2',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.NotRequired[typing.Annotated[int, "metadata"]],
                        id='f3',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=int,
                        id='f4',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.Annotated[typing.Required[int], "metadata"],
                        id='f5',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    InputField(
                        type=typing.NotRequired[typing.Annotated[int, "metadata"]],
                        id='f6',
                        default=NoDefault(),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                params=(
                    Param(
                        field_id='f1',
                        name='f1',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f2',
                        name='f2',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f3',
                        name='f3',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f4',
                        name='f4',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f5',
                        name='f5',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='f6',
                        name='f6',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='f1',
                        default=NoDefault(),
                        accessor=create_key_accessor('f1', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.Annotated[typing.Required[int], "metadata"],
                        id='f2',
                        default=NoDefault(),
                        accessor=create_key_accessor('f2', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.NotRequired[typing.Annotated[int, "metadata"]],
                        id='f3',
                        default=NoDefault(),
                        accessor=create_key_accessor('f3', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=int,
                        id='f4',
                        default=NoDefault(),
                        accessor=create_key_accessor('f4', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.Annotated[typing.Required[int], "metadata"],
                        id='f5',
                        default=NoDefault(),
                        accessor=create_key_accessor('f5', access_error=None),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                    OutputField(
                        type=typing.NotRequired[typing.Annotated[int, "metadata"]],
                        id='f6',
                        default=NoDefault(),
                        accessor=create_key_accessor('f6', access_error=KeyError),
                        metadata=MappingProxyType({}),
                        original=None,
                    ),
                ),
                overriden_types=frozenset({}),
            )
        )
    )
