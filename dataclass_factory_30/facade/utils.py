from types import BuiltinMethodType, MethodType, MethodWrapperType, WrapperDescriptorType
from typing import Any, Callable, Optional, Tuple

from dataclass_factory_30.provider import Chain


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

# pred   value  None
# pred   value  chain
# value  None   None
# value  chain  None


def resolve_pred_value_chain(value_or_pred, value_or_none_or_chain, maybe_chain) -> Tuple[Any, Any, Optional[Chain]]:
    if maybe_chain is not None:
        pred = value_or_pred
        value = value_or_none_or_chain
        chain = maybe_chain
    elif isinstance(value_or_none_or_chain, Chain):
        chain = value_or_none_or_chain
        pred, value = resolve_classmethod(value_or_pred)
    elif value_or_none_or_chain is None:
        if isinstance(value_or_pred, type):
            pred, value = value_or_pred, value_or_pred
        else:
            pred, value = resolve_classmethod(value_or_pred)
        chain = None
    else:
        chain = None
        pred = value_or_pred
        value = value_or_none_or_chain

    return pred, value, chain
