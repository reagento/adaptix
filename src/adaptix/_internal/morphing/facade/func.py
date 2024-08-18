from typing import Any, Optional, TypeVar, overload

from ...common import TypeHint
from .retort import Retort

_global_retort = Retort()
T = TypeVar("T")


@overload
def load(data: Any, tp: type[T], /) -> T:
    ...


@overload
def load(data: Any, tp: TypeHint, /) -> Any:
    ...


def load(data: Any, tp: TypeHint, /):
    return _global_retort.load(data, tp)


@overload
def dump(data: T, tp: type[T], /) -> Any:
    ...


@overload
def dump(data: Any, tp: Optional[TypeHint] = None, /) -> Any:
    ...


def dump(data: Any, tp: Optional[TypeHint] = None, /) -> Any:
    return _global_retort.dump(data, tp)
