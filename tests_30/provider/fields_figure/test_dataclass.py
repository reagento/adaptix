from dataclasses import dataclass, field, InitVar
from types import MappingProxyType
from typing import ClassVar

from dataclass_factory_30.provider import DefaultValue, DefaultFactory
from dataclass_factory_30.provider.fields_figure import (
    DataclassFieldsProvider,
    FieldRM,
    InputFieldRM,
    NoDefault,
    InputFieldsFigure,
    OutputFieldsFigure,
    GetterKind
)
from dataclass_factory_30.provider.request_cls import ParamKind

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
        DataclassFieldsProvider()._get_input_fields_figure(Foo)
        ==
        InputFieldsFigure(
            constructor=Foo,
            extra=None,
            fields=(
                InputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=InitVarInt,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=InitVarInt,
                    name='c',
                    default=DefaultValue(1),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=str,
                    name='d',
                    default=DefaultValue('text'),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=list,
                    name='e',
                    default=DefaultFactory(list),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=int,
                    name='i',
                    default=DefaultValue(4),
                    is_required=False,
                    metadata=MappingProxyType({'meta': 'data'}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )


def test_output():
    assert (
        DataclassFieldsProvider()._get_output_fields_figure(Foo)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=(
                FieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=str,
                    name='d',
                    default=DefaultValue('text'),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=list,
                    name='e',
                    default=DefaultFactory(list),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    name='f',
                    default=DefaultValue(3),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    name='i',
                    default=DefaultValue(4),
                    is_required=True,
                    metadata=MappingProxyType({'meta': 'data'})
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
        DataclassFieldsProvider()._get_input_fields_figure(ChildBar)
        ==
        InputFieldsFigure(
            constructor=ChildBar,
            extra=None,
            fields=(
                InputFieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=int,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ),
        )
    )

    assert (
        DataclassFieldsProvider()._get_output_fields_figure(ChildBar)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=(
                FieldRM(
                    type=int,
                    name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
            ),
        )
    )
