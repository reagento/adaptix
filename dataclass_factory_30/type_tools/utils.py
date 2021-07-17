from typing import List, Any

from ..common import TypeHint

TYPED_DICT_MCS_TUPLE: tuple = ()

try:
    from typing import TypedDict as PyTypedDict  # type: ignore

    class RealPyTypedDict(PyTypedDict):
        pass  # create real class, because PyTypedDict can be helper function

    TYPED_DICT_MCS_TUPLE += (type(RealPyTypedDict),)
except ImportError:
    pass

try:
    from typing_extensions import TypedDict as CompatTypedDict  # type: ignore
    # This is a hack. It exists because typing_extensions.TypedDict
    # is not guaranteed to be a type, it can also be a function (which it is in 3.9)
    _Foo = CompatTypedDict("_Foo", {})

    TYPED_DICT_MCS_TUPLE += (type(_Foo), )
    del _Foo
except ImportError:
    pass


def strip_alias(type_hint: TypeHint) -> TypeHint:
    try:
        return type_hint.__origin__  # type: ignore
    except AttributeError:
        return type_hint


def get_args(type_hint: TypeHint) -> List[TypeHint]:
    try:
        return list(type_hint.__args__)  # type: ignore
    except AttributeError:
        return []


def is_subclass_soft(cls, classinfo) -> bool:
    """Acts like builtin issubclass,
     but returns False instead of rising TypeError
    """
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


def is_new_type(tp) -> bool:
    return hasattr(tp, '__supertype__')


def is_annotated(tp) -> bool:
    return hasattr(tp, '__metadata__')


def is_typed_dict(tp) -> bool:
    if not TYPED_DICT_MCS_TUPLE:
        return False
    return isinstance(tp, TYPED_DICT_MCS_TUPLE)
