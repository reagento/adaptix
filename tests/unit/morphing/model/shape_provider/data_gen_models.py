# mypy: disable-error-code="name-defined, misc"
from typing import Generic, Tuple, TypeVar

from adaptix._internal.feature_requirement import HAS_TV_TUPLE

_T = TypeVar('_T')


@model_spec.decorator
class WithTVField(*model_spec.bases, Generic[_T]):
    a: int
    b: _T


if HAS_TV_TUPLE:
    from typing import TypeVarTuple, Unpack

    ShapeT = TypeVarTuple('ShapeT')
    T = TypeVar('T')
    T1 = TypeVar('T1')
    T2 = TypeVar('T2')

    @model_spec.decorator
    class WithTVTupleBegin(*model_spec.bases, Generic[Unpack[ShapeT], T]):
        a: Tuple[Unpack[ShapeT]]
        b: T

    @model_spec.decorator
    class WithTVTupleEnd(*model_spec.bases, Generic[T, Unpack[ShapeT]]):
        a: T
        b: Tuple[Unpack[ShapeT]]

    @model_spec.decorator
    class WithTVTupleMiddle(*model_spec.bases, Generic[T1, Unpack[ShapeT], T2]):
        a: T1
        b: Tuple[Unpack[ShapeT]]
        c: T2
