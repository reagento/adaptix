from typing import TypeVar, Protocol, Union, Dict, List, Any, ForwardRef
from typing import _SpecialForm

K_contra = TypeVar('K_contra', contravariant=True)
V_co = TypeVar('V_co', covariant=True)


class Parser(Protocol[K_contra, V_co]):
    def __call__(self, arg: K_contra) -> V_co: ...


class Serializer(Protocol[K_contra, V_co]):
    def __call__(self, arg: K_contra) -> V_co: ...


_JsonAtomic = Union[str, int, float, bool, None]
_JsonBasic = Union[_JsonAtomic, list, Dict[str, Any]]
Json = Union[
    Dict[str, _JsonBasic],
    List[_JsonBasic],
    _JsonAtomic
]

TypeHint = Union[type, None, TypeVar, ForwardRef, _SpecialForm]
