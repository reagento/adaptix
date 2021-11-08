import sys
from collections import deque
from typing import Any, Dict, Generic, Type, get_type_hints, Tuple, List, Set, \
    FrozenSet, Deque

from .type_detection import (
    get_self_type_hints, is_generic, is_generic_concrete,
)

if sys.version_info < (3, 9):
    COMPAT_ORIGINS: Dict[Type, Type] = {
        list: List,
        dict: Dict,
        tuple: Tuple,
        set: Set,
        frozenset: FrozenSet,
        deque: Deque,
    }
else:
    COMPAT_ORIGINS = {}


def fill_type_args(args: Dict[Type, Type], type_: Type) -> Type:
    type_ = args.get(type_, type_)
    if is_generic_concrete(type_):
        type_args = tuple(
            args.get(a, a) for a in type_.__args__
        )
        origin = COMPAT_ORIGINS.get(type_.__origin__, type_.__origin__)
        type_ = origin[type_args]
    return type_


def resolve_hints(type_: Type):
    if is_generic_concrete(type_):
        return resolve_concrete_hints(type_)
    if is_generic(type_):
        return resolve_generic_hints(type_)
    return get_type_hints(type_)


def resolve_generic_hints(type_: Type):
    if type_ is Generic:
        return {}
    res = {}
    for base in reversed(type_.__orig_bases__):
        base_hints = resolve_hints(base)
        res.update(base_hints)
    self_hints = get_self_type_hints(type_)
    res.update(self_hints)
    return res


def resolve_concrete_hints(type_: Type):
    if type_.__origin__ is Generic:
        return {}
    hints = resolve_generic_hints(type_.__origin__)
    args = dict(zip(type_.__origin__.__parameters__, type_.__args__))
    res = {
        name: fill_type_args(args, type_)
        for name, type_ in hints.items()
    }
    return res


def resolve_init_hints(type_: Any):
    if not is_generic_concrete(type_):
        return get_type_hints(type_.__init__)
    hints = get_type_hints(type_.__origin__.__init__)
    args = dict(zip(type_.__self__.__origin__.__parameters__, type_.__self__.__args__))
    return {
        name: fill_type_args(args, type_)
        for name, type_ in hints.items()
    }
