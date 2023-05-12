import typing
from dataclasses import InitVar, dataclass, field
from types import MappingProxyType
from typing import ClassVar

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools.definitions import (
    AttrAccessor,
    DefaultFactory,
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    ParamKind,
    Shape,
)
from adaptix._internal.model_tools.introspection import get_dataclass_shape
from tests_helpers import requires

InitVarInt = InitVar[int]  # InitVar comparing by id()


@dataclass
class Foo:
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


def test_input():
    assert (
        get_dataclass_shape(Foo)
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
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='a',
                    ),
                    InputField(
                        type=InitVarInt,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
                    ),
                    InputField(
                        type=InitVarInt,
                        id='c',
                        default=DefaultValue(1),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='c',
                    ),
                    InputField(
                        type=str,
                        id='d',
                        default=DefaultValue('text'),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='d',
                    ),
                    InputField(
                        type=list,
                        id='e',
                        default=DefaultFactory(list),
                        is_required=False,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='e',
                    ),
                    InputField(
                        type=int,
                        id='i',
                        default=DefaultValue(4),
                        is_required=False,
                        metadata=MappingProxyType({'meta': 'data'}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='i',
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
                        accessor=AttrAccessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=str,
                        id='d',
                        default=DefaultValue('text'),
                        accessor=AttrAccessor('d', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=list,
                        id='e',
                        default=DefaultFactory(list),
                        accessor=AttrAccessor('e', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=int,
                        id='f',
                        default=DefaultValue(3),
                        accessor=AttrAccessor('f', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=int,
                        id='i',
                        default=DefaultValue(4),
                        accessor=AttrAccessor('i', is_required=True),
                        metadata=MappingProxyType({'meta': 'data'}),
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
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='a',
                    ),
                    InputField(
                        type=int,
                        id='b',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='b',
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
                        accessor=AttrAccessor('a', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=int,
                        id='b',
                        default=NoDefault(),
                        accessor=AttrAccessor('b', is_required=True),
                        metadata=MappingProxyType({}),
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
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='fr_field',
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
                        accessor=AttrAccessor('fr_field', is_required=True),
                        metadata=MappingProxyType({}),
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
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='fr_field',
                    ),
                    InputField(
                        type=str,
                        id='some_field',
                        default=NoDefault(),
                        is_required=True,
                        metadata=MappingProxyType({}),
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='some_field',
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
                        accessor=AttrAccessor('fr_field', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                    OutputField(
                        type=str,
                        id='some_field',
                        default=NoDefault(),
                        accessor=AttrAccessor('some_field', is_required=True),
                        metadata=MappingProxyType({}),
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
                        param_kind=ParamKind.POS_OR_KW,
                        param_name='annotated_field',
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
                        accessor=AttrAccessor('annotated_field', is_required=True),
                        metadata=MappingProxyType({}),
                    ),
                ),
                overriden_types=frozenset({'annotated_field'}),
            ),
        )
    )
