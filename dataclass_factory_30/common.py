from typing import TypeVar, Union, Dict, List, Any, Callable

K_contra = TypeVar('K_contra', contravariant=True)
V_co = TypeVar('V_co', covariant=True)

Parser = Callable[[Any], V_co]
Serializer = Callable[[K_contra], Any]

_JsonAtomic = Union[str, int, float, bool, None]
_JsonBasic = Union[_JsonAtomic, list, Dict[str, Any]]
Json = Union[
    Dict[str, _JsonBasic],
    List[_JsonBasic],
    _JsonAtomic
]

TypeHint = Any
