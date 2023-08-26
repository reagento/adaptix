import typing
from dataclasses import InitVar, dataclass, field
from types import MappingProxyType
from typing import ClassVar
from unittest.mock import ANY

import pytest

from adaptix._internal.feature_requirement import HAS_ANNOTATED, HAS_PY_310
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
from adaptix._internal.model_tools.introspection import get_dataclass_shape
from tests_helpers import requires

InitVarInt = InitVar[int]  # InitVar comparing by id()


@dataclass
class BasicDataclass:
    a: int
    b: InitVarInt
    c: InitVarInt = field(default=1)
    d: str = 'text'
    e: list = field(default_factory=list)
    f: int = field(default=3, init=False)
    g: ClassVar[int]
    h: ClassVar[int] = 1
    i: int = field(default=4, metadata={'meta': 'data'})

    def __post_init__(self, b: int, c: int):
        pass


def test_basic():
    assert (
        get_dataclass_shape(BasicDataclass)
        ==
        Shape(
            input=InputShape(
                constructor=BasicDataclass,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=InitVarInt,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=InitVarInt,
                        id='c',
                        default=DefaultValue(1),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id='d',
                        default=DefaultValue('text'),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=list,
                        id='e',
                        default=DefaultFactory(list),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='i',
                        default=DefaultValue(4),
                        is_required=False,
                        metadata=MappingProxyType({'meta': 'data'}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='c',
                        name='c',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='d',
                        name='d',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='e',
                        name='e',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='i',
                        name='i',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c', 'd', 'e', 'i'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        accessor=create_attr_accessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id='d',
                        default=DefaultValue('text'),
                        accessor=create_attr_accessor('d', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=list,
                        id='e',
                        default=DefaultFactory(list),
                        accessor=create_attr_accessor('e', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='f',
                        default=DefaultValue(3),
                        accessor=create_attr_accessor('f', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='i',
                        default=DefaultValue(4),
                        accessor=create_attr_accessor('i', is_required=True),
                        metadata=MappingProxyType({'meta': 'data'}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'a', 'd', 'e', 'f', 'i'}),
            )
        )
    )


@dataclass
class Bar:
    a: int


@dataclass
class ChildBar(Bar):
    b: int


def test_inheritance():
    assert (
        get_dataclass_shape(ChildBar)
        ==
        Shape(
            input=InputShape(
                constructor=ChildBar,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'b'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='a',
                        default=NoDefault(),
                        accessor=create_attr_accessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='b',
                        default=NoDefault(),
                        accessor=create_attr_accessor('b', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'b'}),
            ),
        )
    )


@dataclass
class FRParent:
    fr_field: 'int'


@dataclass
class FRChild(FRParent):
    some_field: str


def test_forward_ref():
    assert (
        get_dataclass_shape(FRParent)
        ==
        Shape(
            input=InputShape(
                constructor=FRParent,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='fr_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='fr_field',
                        name='fr_field',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'fr_field'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='fr_field',
                        default=NoDefault(),
                        accessor=create_attr_accessor('fr_field', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'fr_field'}),
            ),
        )
    )

    assert (
        get_dataclass_shape(FRChild)
        ==
        Shape(
            input=InputShape(
                constructor=FRChild,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='fr_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=str,
                        id='some_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='fr_field',
                        name='fr_field',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='some_field',
                        name='some_field',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'some_field'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='fr_field',
                        default=NoDefault(),
                        accessor=create_attr_accessor('fr_field', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=str,
                        id='some_field',
                        default=NoDefault(),
                        accessor=create_attr_accessor('some_field', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'some_field'}),
            )
        )
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    @dataclass
    class WithAnnotated:
        annotated_field: typing.Annotated[int, 'metadata']

    assert (
        get_dataclass_shape(WithAnnotated)
        ==
        Shape(
            input=InputShape(
                constructor=WithAnnotated,
                kwargs=None,
                fields=(
                    InputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='annotated_field',
                        name='annotated_field',
                        kind=ParamKind.POS_OR_KW,
                    ),
                ),
                overriden_types=frozenset({'annotated_field'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=typing.Annotated[int, 'metadata'],
                        id='annotated_field',
                        default=NoDefault(),
                        accessor=create_attr_accessor('annotated_field', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'annotated_field'}),
            ),
        )
    )


@requires(HAS_PY_310)
@pytest.mark.parametrize('case', ['field', 'annotation', 'arg'])
def test_kw_only_at_annotations(case):
    from dataclasses import KW_ONLY

    if case == 'field':
        @dataclass
        class KwOnlyClass:
            a: float
            b: float = field(kw_only=True)
    elif case == 'annotation':
        @dataclass
        class KwOnlyClass:
            a: float
            _: KW_ONLY
            b: float
    elif case == 'arg':
        @dataclass(kw_only=True)
        class KwOnlyClass:
            a: float = field(kw_only=False)
            b: float

    assert (
        get_dataclass_shape(KwOnlyClass)
        ==
        Shape(
            input=InputShape(
                constructor=KwOnlyClass,
                kwargs=None,
                fields=(
                    InputField(
                        type=float,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=float,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=float,
                        id='a',
                        default=NoDefault(),
                        accessor=create_attr_accessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=float,
                        id='b',
                        default=NoDefault(),
                        accessor=create_attr_accessor('b', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'a', 'b'}),
            ),
        )
    )


@requires(HAS_PY_310)
def test_kw_only_false_after_kw_only():
    from dataclasses import KW_ONLY

    @dataclass
    class KwOnlyClass:
        a: float
        _: KW_ONLY
        b: float
        c: float = field(kw_only=False)

    assert (
        get_dataclass_shape(KwOnlyClass)
        ==
        Shape(
            input=InputShape(
                constructor=KwOnlyClass,
                kwargs=None,
                fields=(
                    InputField(
                        type=float,
                        id='a',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=float,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=float,
                        id='c',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='a',
                        name='a',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='c',
                        name='c',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='b',
                        name='b',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=float,
                        id='a',
                        default=NoDefault(),
                        accessor=create_attr_accessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=float,
                        id='b',
                        default=NoDefault(),
                        accessor=create_attr_accessor('b', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=float,
                        id='c',
                        default=NoDefault(),
                        accessor=create_attr_accessor('c', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'a', 'b', 'c'}),
            ),
        )
    )


@requires(HAS_PY_310)
def test_kw_only_inheritance_params_reordering():
    from dataclasses import KW_ONLY

    @dataclass
    class Base:
        x: int = 15.0
        _: KW_ONLY
        z: int = 0
        w: int = 1

    @dataclass
    class Derived(Base):
        y: int = 10
        t: int = field(kw_only=True, default=0)

    assert (
        get_dataclass_shape(Derived)
        ==
        Shape(
            input=InputShape(
                constructor=Derived,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id='x',
                        default=DefaultValue(value=15.0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='z',
                        default=DefaultValue(value=0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='w',
                        default=DefaultValue(value=1),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='y',
                        default=DefaultValue(value=10),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    InputField(
                        type=int,
                        id='t',
                        default=DefaultValue(value=0),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                params=(
                    Param(
                        field_id='x',
                        name='x',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='y',
                        name='y',
                        kind=ParamKind.POS_OR_KW,
                    ),
                    Param(
                        field_id='z',
                        name='z',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='w',
                        name='w',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='t',
                        name='t',
                        kind=ParamKind.KW_ONLY,
                    ),
                ),
                overriden_types=frozenset({'y', 't'}),
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id='x',
                        default=DefaultValue(value=15.0),
                        accessor=create_attr_accessor('x', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='z',
                        default=DefaultValue(value=0),
                        accessor=create_attr_accessor('z', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='w',
                        default=DefaultValue(value=1),
                        accessor=create_attr_accessor('w', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='y',
                        default=DefaultValue(value=10),
                        accessor=create_attr_accessor('y', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                    OutputField(
                        type=int,
                        id='t',
                        default=DefaultValue(value=0),
                        accessor=create_attr_accessor('t', is_required=True),
                        metadata=MappingProxyType({}),
                        original=ANY,
                    ),
                ),
                overriden_types=frozenset({'y', 't'}),
            ),
        )
    )
