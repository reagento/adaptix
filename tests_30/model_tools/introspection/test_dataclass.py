from dataclasses import InitVar, dataclass, field
from types import MappingProxyType
from typing import ClassVar

from dataclass_factory_30.model_tools import (
    AttrAccessor,
    DefaultFactory,
    DefaultValue,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    get_dataclass_input_figure,
    get_dataclass_output_figure,
)

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
        get_dataclass_input_figure(Foo)
        ==
        InputFigure(
            constructor=Foo,
            extra=None,
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
                    type=InitVarInt,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
                InputField(
                    type=InitVarInt,
                    name='c',
                    default=DefaultValue(1),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='c',
                ),
                InputField(
                    type=str,
                    name='d',
                    default=DefaultValue('text'),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='d',
                ),
                InputField(
                    type=list,
                    name='e',
                    default=DefaultFactory(list),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='e',
                ),
                InputField(
                    type=int,
                    name='i',
                    default=DefaultValue(4),
                    is_required=False,
                    metadata=MappingProxyType({'meta': 'data'}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='i',
                ),
            ),
        )
    )


def test_output():
    assert (
        get_dataclass_output_figure(Foo)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=str,
                    name='d',
                    default=DefaultValue('text'),
                    accessor=AttrAccessor('d', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=list,
                    name='e',
                    default=DefaultFactory(list),
                    accessor=AttrAccessor('e', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='f',
                    default=DefaultValue(3),
                    accessor=AttrAccessor('f', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='i',
                    default=DefaultValue(4),
                    accessor=AttrAccessor('i', is_required=True),
                    metadata=MappingProxyType({'meta': 'data'}),
                ),
            ),
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
        get_dataclass_input_figure(ChildBar)
        ==
        InputFigure(
            constructor=ChildBar,
            extra=None,
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
                    type=int,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
            ),
        )
    )

    assert (
        get_dataclass_output_figure(ChildBar)
        ==
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    accessor=AttrAccessor('a', is_required=True),
                    metadata=MappingProxyType({}),
                ),
                OutputField(
                    type=int,
                    name='b',
                    default=NoDefault(),
                    accessor=AttrAccessor('b', is_required=True),
                    metadata=MappingProxyType({}),
                ),
            ),
        )
    )
