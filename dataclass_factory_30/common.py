from typing import TypeVar, Any, Callable, Tuple, Union, Type

K_contra = TypeVar('K_contra', contravariant=True)
V_co = TypeVar('V_co', covariant=True)
T = TypeVar('T')

Parser = Callable[[Any], V_co]
Serializer = Callable[[K_contra], Any]

TypeHint = Any

VarTuple = Tuple[T, ...]

Catchable = Union[Type[BaseException], VarTuple[Type[BaseException]]]
