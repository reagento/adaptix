import inspect
from enum import Enum

from typing import (
    Collection, Tuple, Optional, Any, Dict, Union, Type,
    TypeVar, Generic, List, )

LITERAL_TYPES: List[Any] = []
TYPED_DICT_METAS_TMP: List[Any] = []
try:
    from typing import Literal as PyLiteral  # type: ignore

    LITERAL_TYPES.append(PyLiteral)
except ImportError:
    pass

try:
    CompatLiteral: Any
    from typing_extensions import Literal as CompatLiteral  # type: ignore

    LITERAL_TYPES.append(CompatLiteral)
except ImportError:
    CompatLiteral = None

try:
    from typing import TypedDict as PyTypedDict  # type: ignore

    TYPED_DICT_METAS_TMP.append(type(PyTypedDict))
except ImportError:
    pass

try:
    from typing_extensions import TypedDict as CompatTypedDict  # type: ignore

    TYPED_DICT_METAS_TMP.append(type(CompatTypedDict))
except ImportError:
    pass

TYPED_DICT_METAS = tuple(TYPED_DICT_METAS_TMP)
del TYPED_DICT_METAS_TMP


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
        return (
                issubclass_safe(type_, tuple) or
                issubclass_safe(type_.__origin__, Tuple) or
                issubclass_safe(type_, Tuple)
        )
    except AttributeError:
        return False


def is_collection(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return issubclass_safe(type_, Collection) or issubclass_safe(type_.__origin__, Collection)
    except AttributeError:
        return False


def is_typeddict(type_) -> bool:
    if not TYPED_DICT_METAS:
        return False
    return isinstance(type_, TYPED_DICT_METAS)


def is_optional(type_) -> bool:
    return issubclass_safe(type_, Optional)


def is_union(type_: Type) -> bool:
    try:
        return issubclass_safe(type_.__origin__, Union)
    except AttributeError:
        return False


def is_any(type_: Type) -> bool:
    return type_ in (Any, inspect.Parameter.empty)


def is_generic_concrete(type_: Type) -> bool:
    return getattr(type_, "__origin__", None) is not None


def is_generic(type_: Type) -> bool:
    return issubclass_safe(type_, Generic)


def is_none(type_: Type) -> bool:
    return type_ is type(None)


def is_enum(cls: Type) -> bool:
    return issubclass_safe(cls, Enum)


def args_unspecified(cls: Type) -> bool:
    return (
            not hasattr(cls, '__args__') or
            not hasattr(cls, '__parameters__') or
            (not cls.__args__ and cls.__parameters__) or
            (cls.__args__ == cls.__parameters__)
    )


def is_literal(cls) -> bool:
    return is_generic_concrete(cls) and cls.__origin__ in LITERAL_TYPES


def is_literal36(cls) -> bool:
    if not CompatLiteral:
        return False
    try:
        return cls == CompatLiteral[cls.__values__]
    except AttributeError:
        return False


def is_dict(cls) -> bool:
    try:
        dicts = (dict, Dict)
        return cls in dicts or cls.__origin__ in dicts
    except AttributeError:
        return False


def is_type_var(type_: Type) -> bool:
    return type(type_) is TypeVar
