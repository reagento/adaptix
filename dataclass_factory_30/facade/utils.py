from types import BuiltinMethodType, MethodType, MethodWrapperType, WrapperDescriptorType
from typing import Any, Callable, Tuple


def resolve_classmethod(func) -> Tuple[type, Callable]:
    if isinstance(func, (MethodType, BuiltinMethodType, MethodWrapperType)):
        bound = func.__self__
    elif isinstance(func, WrapperDescriptorType):
        bound = func.__objclass__
    else:
        raise ValueError

    if not isinstance(bound, type):
        raise ValueError

    return bound, func


def resolve_pred_and_value(value_or_pred, value_or_none) -> Tuple[Any, Any]:
    value: Any
    if value_or_none is None:
        if isinstance(value_or_pred, type):
            pred = value_or_pred
            value = value_or_pred
        else:
            pred, value = resolve_classmethod(value_or_pred)
    else:
        pred = value_or_pred
        value = value_or_none

    return pred, value
