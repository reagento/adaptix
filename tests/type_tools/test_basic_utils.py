from collections import namedtuple
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    NamedTuple,
    Protocol,
    SupportsInt,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)

from adaptix._internal.feature_requirement import HAS_STD_CLASSES_GENERICS
from adaptix._internal.type_tools import is_named_tuple_class, is_protocol, is_user_defined_generic
from adaptix._internal.type_tools.basic_utils import get_type_vars_of_parametrized, is_parametrized


class NTParent(NamedTuple):
    a: int
    b: int


class NTChild(NTParent):
    c: int


DynNTParent = namedtuple('DynNTParent', 'a, b')


class DynNTChild(DynNTParent):
    c: int


def test_is_named_tuple_class():
    assert is_named_tuple_class(NTParent)
    assert is_named_tuple_class(NTChild)
    assert is_named_tuple_class(DynNTParent)
    assert is_named_tuple_class(DynNTChild)


class FooProto(Protocol):
    def foo(self) -> bool:
        pass


@runtime_checkable
class RtFooProto(Protocol):
    def foo(self) -> bool:
        pass


class ImplFooProto:
    def foo(self) -> bool:
        pass


class InheritedImplFooProto(FooProto):
    def foo(self) -> bool:
        pass


class InheritedImplRtFooProto(RtFooProto):
    def foo(self) -> bool:
        pass


def test_is_protocol():
    assert not is_protocol(Protocol)
    assert is_protocol(Proto)
    assert is_protocol(RtFooProto)
    assert is_protocol(SupportsInt)

    assert not is_protocol(InheritedImplFooProto)
    assert not is_protocol(InheritedImplRtFooProto)

    assert not is_protocol(ImplFooProto)
    assert not is_protocol(int)
    assert not is_protocol(type)
    assert not is_protocol(object)

    assert not is_protocol(15)
    assert not is_protocol('15')

    class ExtProto(Proto, Protocol):
        def bar(self):
            pass

    assert is_protocol(ExtProto)


T = TypeVar('T', covariant=True)  # make it covariant to use at protocol


class Gen(Generic[T]):
    pass


class GenChildImplicit(Gen):
    pass


class GenChildExplicit(Gen[int]):
    pass


class GenChildExplicitTypeVar(Gen[T]):
    pass


V = TypeVar('V')


class GenGen(Gen[int], Generic[T]):
    pass


def test_is_user_defined_generic():
    assert is_user_defined_generic(Gen)
    assert is_user_defined_generic(Gen[V])
    assert not is_user_defined_generic(Gen[int])

    assert not is_user_defined_generic(GenChildImplicit)
    assert not is_user_defined_generic(GenChildExplicit)

    assert is_user_defined_generic(GenChildExplicitTypeVar)
    assert is_user_defined_generic(GenChildExplicitTypeVar[V])
    assert not is_user_defined_generic(GenChildExplicitTypeVar[int])

    assert is_user_defined_generic(GenGen)
    assert is_user_defined_generic(GenGen[V])
    assert not is_user_defined_generic(GenGen[int])

    assert not is_user_defined_generic(Tuple)
    assert not is_user_defined_generic(Tuple[V])
    assert not is_user_defined_generic(Tuple[int])


class Proto(Protocol[T]):
    pass


class ProtoChildImplicit(Proto):
    pass


class ProtoChildExplicit(Proto[int]):
    pass


class ProtoChildExplicitTypeVar(Proto[T]):
    pass


class ProtoProto(Proto[int], Protocol[T]):
    pass


def test_is_user_defined_generic_protocol():
    assert is_user_defined_generic(Proto)
    assert is_user_defined_generic(Proto[V])
    assert not is_user_defined_generic(Proto[int])

    assert not is_user_defined_generic(ProtoChildImplicit)
    assert not is_user_defined_generic(ProtoChildExplicit)

    assert is_user_defined_generic(ProtoChildExplicitTypeVar)
    assert is_user_defined_generic(ProtoChildExplicitTypeVar[V])
    assert not is_user_defined_generic(ProtoChildExplicitTypeVar[int])

    assert is_user_defined_generic(ProtoProto)
    assert is_user_defined_generic(ProtoProto[V])
    assert not is_user_defined_generic(ProtoProto[int])


def test_is_parametrized():
    assert not is_parametrized(int)
    assert not is_parametrized(List)
    assert not is_parametrized(list)

    assert is_parametrized(List[int])
    assert is_parametrized(List[T])

    if HAS_STD_CLASSES_GENERICS:
        assert is_parametrized(list[int])
        assert is_parametrized(list[T])

    assert not is_parametrized(Union)
    assert is_parametrized(Union[int, str])

    # do not test all special cases of typing like Annotated, rely on get_args


def test_get_type_vars_of_parametrized():
    assert get_type_vars_of_parametrized(Gen[T]) == (T,)
    assert get_type_vars_of_parametrized(Gen[str]) == ()
    assert get_type_vars_of_parametrized(Gen) == ()

    assert get_type_vars_of_parametrized(Proto[T]) == (T, )
    assert get_type_vars_of_parametrized(Proto[str]) == ()
    assert get_type_vars_of_parametrized(Proto) == ()

    assert get_type_vars_of_parametrized(list) == ()
    assert get_type_vars_of_parametrized(List[T]) == (T, )
    assert get_type_vars_of_parametrized(List) == ()
    assert get_type_vars_of_parametrized(List[str]) == ()

    assert get_type_vars_of_parametrized(dict) == ()
    assert get_type_vars_of_parametrized(Dict[T, V]) == (T, V)
    assert get_type_vars_of_parametrized(Dict) == ()
    assert get_type_vars_of_parametrized(Dict[str, V]) == (V, )
    assert get_type_vars_of_parametrized(Dict[T, str]) == (T, )
    assert get_type_vars_of_parametrized(Dict[str, str]) == ()
    assert get_type_vars_of_parametrized(Dict[V, T]) == (V, T)

    assert get_type_vars_of_parametrized(tuple) == ()
    assert get_type_vars_of_parametrized(Tuple) == ()
    assert get_type_vars_of_parametrized(Tuple[()]) == ()
    assert get_type_vars_of_parametrized(Tuple[int]) == ()
    assert get_type_vars_of_parametrized(Tuple[int, T]) == (T, )

    assert get_type_vars_of_parametrized(Callable) == ()
    assert get_type_vars_of_parametrized(Callable[..., Any]) == ()
    assert get_type_vars_of_parametrized(Callable[[int], Any]) == ()
    assert get_type_vars_of_parametrized(Callable[[T], Any]) == (T, )
    assert get_type_vars_of_parametrized(Callable[[T], T]) == (T, )
    assert get_type_vars_of_parametrized(Callable[[T, int, V], T]) == (T, V)

    if HAS_STD_CLASSES_GENERICS:
        assert get_type_vars_of_parametrized(list[T]) == (T, )
        assert get_type_vars_of_parametrized(list[str]) == ()
        assert get_type_vars_of_parametrized(dict[T, V]) == (T, V)
        assert get_type_vars_of_parametrized(dict[str, V]) == (V,)
        assert get_type_vars_of_parametrized(dict[T, str]) == (T,)
        assert get_type_vars_of_parametrized(dict[str, str]) == ()
        assert get_type_vars_of_parametrized(dict[V, T]) == (V, T)

        assert get_type_vars_of_parametrized(tuple[()]) == ()
        assert get_type_vars_of_parametrized(tuple[int]) == ()
        assert get_type_vars_of_parametrized(tuple[int, T]) == (T,)

    assert get_type_vars_of_parametrized(Generic) == ()
    assert get_type_vars_of_parametrized(Generic[T]) == (T, )
    assert get_type_vars_of_parametrized(Generic[T, V]) == (T, V)



