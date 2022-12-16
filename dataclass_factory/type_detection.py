import inspect
import sys
from collections import defaultdict
from enum import Enum
from typing import (
    Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar,
    Union, get_type_hints, Iterable, DefaultDict,
)
from warnings import warn

LITERAL_TYPES: List[Any] = []
TYPED_DICT_METAS_TMP: List[Any] = []
try:
    from typing import Literal as PyLiteral  # type: ignore

    LITERAL_TYPES.append(PyLiteral)
except ImportError:
    pass

try:
    from typing_extensions import NotRequired, Required
except ImportError:
    Required = NotRequired = None

try:
    CompatLiteral: Any
    from typing_extensions import Literal as CompatLiteral  # type: ignore

    LITERAL_TYPES.append(CompatLiteral)
except ImportError:
    CompatLiteral = None

try:
    from types import UnionType  # type: ignore
except ImportError:
    UnionType = None  # type: ignore

try:
    from typing import TypedDict as PyTypedDict  # type: ignore


    class RealPyTypedDict(PyTypedDict):
        pass  # create real class, because PyTypedDict can be helper function


    TYPED_DICT_METAS_TMP.append(type(RealPyTypedDict))
except ImportError:
    PyTypedDict = None

try:
    from typing_extensions import TypedDict as CompatTypedDict  # type: ignore

    # This is a hack. It exists because typing_extensions.TypedDict
    # is not guaranteed to be a type, it can also be a function (which it is in 3.9)
    _Foo = CompatTypedDict("_Foo", {})
    TYPED_DICT_METAS_TMP.append(type(_Foo))
    del _Foo
except ImportError:
    pass

TYPED_DICT_METAS = tuple(TYPED_DICT_METAS_TMP)
del TYPED_DICT_METAS_TMP


class TypedDictAt38Warning(UserWarning):
    def __str__(self):
        return (
            "Runtime introspection of TypedDict at python3.8 and lower does not support inheritance."
            " Please, update python or consider limitations suppressing this warning"
        )


HAS_PY_39 = sys.version_info >= (3, 9)


def get_keys_from_normal_typed_dict(tp, fields):
    required_keys = tp.__required_keys__
    return {
        f.field_name
        for f in fields
        if f.field_name in required_keys
    }


if HAS_PY_39:
    def get_required_fields(tp, fields):
        return get_keys_from_normal_typed_dict(tp, fields)
else:
    def get_required_fields(tp, fields):
        typing_extensions_td = TYPED_DICT_METAS[-1]
        if isinstance(tp, typing_extensions_td):  # type: ignore
            return get_keys_from_normal_typed_dict(tp, fields)
        warn(TypedDictAt38Warning(), stacklevel=3)
        total = tp.__total__
        if total:
            return {f.field_name for f in fields}
        return set()


def check_for_required_and_not_required(type_: Type) -> bool:
    if not all([PyTypedDict, CompatTypedDict]):
        return False
    typing_extensions_td = TYPED_DICT_METAS[0]
    typing_td = TYPED_DICT_METAS[1]

    is_old_typed_dict = not isinstance(
        type_, typing_extensions_td) and isinstance(type_, typing_td)  # type: ignore
    if not is_old_typed_dict:
        return False
    annotations = type_.__annotations__
    for tp in annotations:
        result = is_required_or_not_required(annotations[tp])
        if result:
            return True
    return False


def is_required_or_not_required(type_: Type) -> bool:
    if all([Required, NotRequired]):  # type: ignore
        origin = getattr(type_, "__origin__", None)
        if origin is not None and origin in (NotRequired, Required):  # type: ignore
            return True
    return False


def get_self_type_hints(cls: Type) -> Dict[str, Type]:
    """
    Returns type hints declared in current class without inherited once
    """
    # use __dict__ to fix if __annotations__ is inherited
    annotations = cls.__dict__.get("__annotations__", {})
    return {
        field: type_
        for field, type_ in get_type_hints(cls).items()
        if field in annotations
    }


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


def is_newtype(type_) -> bool:
    return hasattr(type_, "__supertype__") and hasattr(type_, "__name__")


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


def is_iterable(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return issubclass_safe(type_, Iterable) or issubclass_safe(type_.__origin__, Iterable)
    except AttributeError:
        return False


def is_typeddict(type_) -> bool:
    if not TYPED_DICT_METAS:
        return False
    return isinstance(type_, TYPED_DICT_METAS)


def is_namedtuple(type_) -> bool:
    # we check only `_fields` class attribute,
    # so user can create own typeddict-like classes with minimal implementation
    return issubclass_safe(type_, tuple) \
        and hasattr(type_, "_fields") \
        and hasattr(type_, "_make") \
        and hasattr(type_, "_asdict") \
        and hasattr(type_, "_replace")


def is_optional(type_) -> bool:
    return issubclass_safe(type_, Optional)


def is_union(type_: Type) -> bool:
    try:
        return issubclass_safe(type_.__origin__, Union)
    except AttributeError:
        pass
    if UnionType is not None:
        return isinstance(type_, UnionType)
    return False


def is_any(type_: Type) -> bool:
    return type_ in (Any, inspect.Parameter.empty)


def is_generic_concrete(type_: Type) -> bool:
    return (
        getattr(type_, "__origin__", None) is not None and
        getattr(type_, "__args__", None) is not None
    )


def is_generic(type_: Type) -> bool:
    # some classes like Protocol inherit from Generic
    # but do not act like generics unless they are parametrized
    # we can check if it is a true Generic by checking `__orig_bases__`
    return issubclass_safe(type_, Generic) and hasattr(type_, "__orig_bases__")


def is_none(type_: Type) -> bool:
    return type_ in (None, type(None))  # noqa E721 because of https://github.com/python/mypy/issues/3060


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
        dicts = (dict, Dict, defaultdict, DefaultDict)
        return cls in dicts or cls.__origin__ in dicts
    except AttributeError:
        return False


def is_type_var(type_: Type) -> bool:
    return type(type_) is TypeVar


def instance_wont_have_dict(cls) -> bool:
    try:
        dict_offset_sign = cls.__dictoffset__ == 0
    except AttributeError:
        dict_offset_sign = False

    slots_sign = hasattr(cls, '__slots__') and '__dict__' not in cls.__slots__

    return dict_offset_sign or slots_sign
