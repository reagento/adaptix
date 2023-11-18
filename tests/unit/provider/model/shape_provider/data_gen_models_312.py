from typing import Tuple, Unpack


@model_spec.decorator
class WithTVField[_T](*model_spec.bases):
    a: int
    b: _T


@model_spec.decorator
class WithTVTupleBegin[*ShapeT, T](*model_spec.bases):
    a: Tuple[Unpack[ShapeT]]
    b: T


@model_spec.decorator
class WithTVTupleEnd[T, *ShapeT](*model_spec.bases):
    a: T
    b: Tuple[Unpack[ShapeT]]


@model_spec.decorator
class WithTVTupleMiddle[T1, *ShapeT, T2](*model_spec.bases):
    a: T1
    b: Tuple[Unpack[ShapeT]]
    c: T2
