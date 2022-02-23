from types import MappingProxyType
from typing import TypedDict

from dataclass_factory_30.provider import NoDefault
from dataclass_factory_30.provider.fields_figure import (
    TypedDictFieldsProvider,
    FieldRM,
    InputFieldsFigure,
    OutputFieldsFigure,
    _to_inp, _to_out
)
from dataclass_factory_30.provider.request_cls import ParamKind, AccessKind


class Foo(TypedDict, total=True):
    a: int
    b: str


class Bar(TypedDict, total=False):
    a: int
    b: str


TOTAL_FIELDS = (
    FieldRM(
        type=int,
        name='a',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({})
    ),
    FieldRM(
        type=str,
        name='b',
        default=NoDefault(),
        is_required=True,
        metadata=MappingProxyType({})
    ),
)


def test_total_input():
    assert (
        TypedDictFieldsProvider()._get_input_fields_figure(Foo)
        ==
        InputFieldsFigure(
            constructor=Foo,
            extra=None,
            fields=_to_inp(ParamKind.KW_ONLY, TOTAL_FIELDS),
        )
    )


def test_total_output():
    assert (
        TypedDictFieldsProvider()._get_output_fields_figure(Foo)
        ==
        OutputFieldsFigure(
            extra=None,
            fields=_to_out(AccessKind.ITEM, TOTAL_FIELDS),
        )
    )


NON_TOTAL_FIELDS = (
    FieldRM(
        type=int,
        name='a',
        default=NoDefault(),
        is_required=False,
        metadata=MappingProxyType({})
    ),
    FieldRM(
        type=str,
        name='b',
        default=NoDefault(),
        is_required=False,
        metadata=MappingProxyType({})
    ),
)


def test_non_total_input():
    assert (
        TypedDictFieldsProvider()._get_input_fields_figure(Bar)
        ==
        InputFieldsFigure(
            constructor=Bar,
            extra=None,
            fields=_to_inp(ParamKind.KW_ONLY, NON_TOTAL_FIELDS),
        )
    )


def test_non_total_output():
    assert (
        TypedDictFieldsProvider()._get_output_fields_figure(Bar)
        ==
        OutputFieldsFigure(
            extra=None,
            fields=_to_out(AccessKind.ITEM, NON_TOTAL_FIELDS),
        )
    )
