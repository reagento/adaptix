from typing import Generic, Iterable, Tuple

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

    TYPED_DICT_MCS_TUPLE += (type(_Foo),)
    del _Foo
except ImportError:
    pass


def strip_alias(type_hint: TypeHint) -> TypeHint:
    try:
        return type_hint.__origin__  # type: ignore
    except AttributeError:
        return type_hint


def get_args(type_hint: TypeHint) -> Tuple[TypeHint, ...]:
    try:
        return tuple(type_hint.__args__)  # type: ignore
    except AttributeError:
        return ()


def is_subclass_soft(cls, classinfo) -> bool:
    """Acts like builtin issubclass,
     but returns False instead of rising TypeError
    """
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


def has_attrs(obj, attrs: Iterable[str]) -> bool:
    return all(
        hasattr(obj, attr_name)
        for attr_name in attrs
    )


def is_new_type(tp) -> bool:
    return has_attrs(tp, ['__supertype__', '__name__'])


def is_annotated(tp) -> bool:
    return has_attrs(tp, ['__metadata__', '__origin__'])


def is_typed_dict_class(tp) -> bool:
    if not TYPED_DICT_MCS_TUPLE:
        return False
    return isinstance(tp, TYPED_DICT_MCS_TUPLE)


NAMED_TUPLE_METHODS = ('_fields', '_field_defaults', '_make', '_replace', '_asdict')


def is_named_tuple_class(tp) -> bool:
    return (
        is_subclass_soft(tp, tuple)
        and
        has_attrs(tp, NAMED_TUPLE_METHODS)
    )


def is_user_defined_generic(tp) -> bool:
    return (
        hasattr(tp, '__parameters__')
        and tp.__parameters__
        and is_subclass_soft(strip_alias(tp), Generic)  # throw away builtin generics
    )


def is_protocol(tp):
    from typing import Protocol

    if not isinstance(tp, type):
        return False

    return Protocol in tp.__bases__
