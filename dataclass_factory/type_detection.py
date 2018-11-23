import inspect
from typing import Collection, Tuple, Optional, ClassVar, Any, T, KT, VT


def hasargs(type_, *args):
    try:
        if not type_.__args__:
            return False
        res = all(arg in type_.__args__ for arg in args)
    except AttributeError:
        return False
    else:
        return res


def issubclass_safe(cls, classinfo):
    try:
        result = issubclass(cls, classinfo)
    except Exception:
        return False
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
    return issubclass_safe(type_, Optional) or hasargs(type_, type(None))


def is_union(type_: ClassVar) -> bool:
    try:
        return bool(type_.__args__)
    except:
        return False


def is_any(type_: ClassVar) -> bool:
    return type_ in (Any, T, KT, VT, inspect._empty)
