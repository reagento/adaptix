from types import MethodType, BuiltinMethodType
from typing import Tuple, Callable

from ..type_tools import normalize_type, is_generic


def resolve_classmethod(func) -> Tuple[type, Callable]:
    if not isinstance(func, (MethodType, BuiltinMethodType)):
        raise ValueError(
            'as_constructor() with one argument expects classmethod'
        )

    bound = func.__self__

    if not isinstance(bound, type):
        raise ValueError(
            'as_constructor() with one argument expects classmethod'
        )

    if is_generic(normalize_type(bound)):
        raise ValueError(
            'as_constructor() with one argument does not support generic'
        )

    return bound, func
