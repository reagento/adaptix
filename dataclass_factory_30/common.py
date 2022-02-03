from typing import TypeVar, Any, Callable

K_contra = TypeVar('K_contra', contravariant=True)
V_co = TypeVar('V_co', covariant=True)

Parser = Callable[[Any], V_co]
Serializer = Callable[[K_contra], Any]

TypeHint = Any
