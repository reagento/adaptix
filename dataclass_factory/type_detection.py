import inspect
from enum import Enum

from typing import Collection, Tuple, Optional, Any, Dict, Union, Type, TypeVar


def hasargs(type_, *args) -> bool:
    try:
        if not type_.__args__:
            return False
        res = all(arg in type_.__args__ for arg in args)
    except AttributeError:
        return False
    else:
        return res


def issubclass_safe(cls, classinfo) -> bool:
    try:
        result = issubclass(cls, classinfo)
    except Exception:
        return cls is classinfo
    else:
        return result


def is_tuple(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return issubclass_safe(type_.__origin__, Tuple) or issubclass_safe(type_, Tuple)
    except AttributeError:
        return False


def is_collection(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return issubclass_safe(type_.__origin__, Collection) or issubclass_safe(type_, Collection)
    except AttributeError:
        return False


def is_optional(type_) -> bool:
    return issubclass_safe(type_, Optional)


def is_union(type_: Type) -> bool:
    try:
        return issubclass_safe(type_.__origin__, Union)
    except AttributeError:
        return False


def is_any(type_: Type) -> bool:
    return type_ in (Any, inspect.Parameter.empty)


def is_generic(type_: Type) -> bool:
    return hasattr(type_, "__origin__")


def is_none(type_: Type) -> bool:
    return type_ is type(None)


def is_enum(cls: Type) -> bool:
    return issubclass_safe(cls, Enum)


def args_unspecified(cls: Type) -> bool:
    return (
            (not cls.__args__ and cls.__parameters__) or
            (cls.__args__ == cls.__parameters__)
    )


def is_dict(cls) -> bool:
    try:
        origin = cls.__origin__ or cls
        return origin in (dict, Dict)
    except AttributeError:
        return False


def is_type_var(type_: Type) -> bool:
    return type(type_) is TypeVar


def fill_type_args(args: Dict[Type, Type], type_: Type) -> Type:
    type_ = args.get(type_, type_)
    if is_generic(type_):
        type_args = tuple(
            args.get(a, a) for a in type_.__args__
        )
        type_ = type_.__origin__[type_args]
    return type_
