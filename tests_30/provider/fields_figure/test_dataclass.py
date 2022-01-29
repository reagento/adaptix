from dataclasses import dataclass, field
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


@dataclass
class Foo:
    a: int
    b: str = 'text'
    c: list = field(default_factory=list)
    d: int = field(default=3, init=False)
    e: ClassVar[int]
    f: ClassVar[int] = 1
    g: int = field(default=4, metadata={'meta': 'data'})


def test_input():
    assert (
        DataclassFieldsProvider()._get_input_fields_figure(Foo)
        ==
        InputFieldsFigure(
            extra=None,
            fields=[
                InputFieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=str,
                    field_name='b',
                    default=DefaultValue('text'),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=list,
                    field_name='c',
                    default=DefaultFactory(list),
                    is_required=False,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=int,
                    field_name='g',
                    default=DefaultValue(4),
                    is_required=False,
                    metadata=MappingProxyType({'meta': 'data'}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ],
        )
    )


def test_output():
    assert (
        DataclassFieldsProvider()._get_output_fields_figure(Foo)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=[
                FieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=str,
                    field_name='b',
                    default=DefaultValue('text'),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=list,
                    field_name='c',
                    default=DefaultFactory(list),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    field_name='d',
                    default=DefaultValue(3),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    field_name='g',
                    default=DefaultValue(4),
                    is_required=True,
                    metadata=MappingProxyType({'meta': 'data'})
                ),
            ],
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
            extra=None,
            fields=[
                InputFieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    type=int,
                    field_name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ],
        )
    )

    assert (
        DataclassFieldsProvider()._get_output_fields_figure(ChildBar)
        ==
        OutputFieldsFigure(
            getter_kind=GetterKind.ATTR,
            fields=[
                FieldRM(
                    type=int,
                    field_name='a',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
                FieldRM(
                    type=int,
                    field_name='b',
                    default=NoDefault(),
                    is_required=True,
                    metadata=MappingProxyType({})
                ),
            ],
        )
    )
