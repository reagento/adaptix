from typing import Unpack

from tests_helpers import ModelSpec


@model_spec.decorator
class WithTVField[_T](*model_spec.bases):
    a: int
    b: _T


if model_spec.kind != ModelSpec.PYDANTIC:
    @model_spec.decorator
    class WithTVTupleBegin[*ShapeT, T](*model_spec.bases):
        a: tuple[Unpack[ShapeT]]
        b: T


    @model_spec.decorator
    class WithTVTupleEnd[T, *ShapeT](*model_spec.bases):
        a: T
        b: tuple[Unpack[ShapeT]]


    @model_spec.decorator
    class WithTVTupleMiddle[T1, *ShapeT, T2](*model_spec.bases):
        a: T1
        b: tuple[Unpack[ShapeT]]
        c: T2
