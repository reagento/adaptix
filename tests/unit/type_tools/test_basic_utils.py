import collections
import typing
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
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

import pytest
from tests_helpers import cond_list, load_namespace

from adaptix._internal.feature_requirement import HAS_ANNOTATED, HAS_PY_312, HAS_STD_CLASSES_GENERICS
from adaptix._internal.type_tools import is_named_tuple_class, is_protocol, is_user_defined_generic
from adaptix._internal.type_tools.basic_utils import (
    get_type_vars_of_parametrized,
    is_bare_generic,
    is_generic,
    is_generic_class,
    is_parametrized,
)


class NTParent(NamedTuple):
    a: int
    b: int


class NTChild(NTParent):
    c: int


DynNTParent = namedtuple("DynNTParent", "a, b")  # noqa: PYI024


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
    assert not is_protocol("15")

    class ExtProto(Proto, Protocol):
        def bar(self):
            pass

    assert is_protocol(ExtProto)


_GEN_NS_LIST = [
    load_namespace("data_generics.py", "inheritance"),
    *cond_list(HAS_PY_312, lambda: [load_namespace("data_generics_312.py", "syntax_sugar")]),
]


@pytest.fixture(params=[pytest.param(ns, id=ns.__ns_id__) for ns in _GEN_NS_LIST])
def gen_ns(request):
    return request.param


def gen_ns_parametrize(*functions: Callable[[Any], Any]):
    return [
        func(ns)
        for func in functions
        for ns in _GEN_NS_LIST
    ]


_TYPE_ALIAS_NS = load_namespace("data_type_alias_312.py") if HAS_PY_312 else None


def type_alias_ns_parametrize(*functions: Callable[[Any], Any]):
    return [func(_TYPE_ALIAS_NS) for func in functions] if _TYPE_ALIAS_NS is not None else []


def test_is_user_defined_generic(gen_ns):
    assert is_user_defined_generic(gen_ns.Gen)
    assert is_user_defined_generic(gen_ns.Gen[V])
    assert not is_user_defined_generic(gen_ns.Gen[int])

    assert not is_user_defined_generic(gen_ns.GenChildImplicit)
    assert not is_user_defined_generic(gen_ns.GenChildExplicit)

    assert is_user_defined_generic(gen_ns.GenChildExplicitTypeVar)
    assert is_user_defined_generic(gen_ns.GenChildExplicitTypeVar[V])
    assert not is_user_defined_generic(gen_ns.GenChildExplicitTypeVar[int])

    assert is_user_defined_generic(gen_ns.GenGen)
    assert is_user_defined_generic(gen_ns.GenGen[V])
    assert not is_user_defined_generic(gen_ns.GenGen[int])

    assert not is_user_defined_generic(Tuple)
    assert not is_user_defined_generic(Tuple[V])
    assert not is_user_defined_generic(Tuple[int])

    assert not is_user_defined_generic(Generic)
    assert is_user_defined_generic(Generic[V])
    # Generic[V][int] raises error

    assert not is_user_defined_generic(Protocol)
    assert is_user_defined_generic(Protocol[V])
    # Protocol[V][int] raises error

    if _TYPE_ALIAS_NS is not None:
        assert not is_user_defined_generic(_TYPE_ALIAS_NS.IntAlias)
        assert not is_user_defined_generic(_TYPE_ALIAS_NS.RecursiveAlias)
        assert is_user_defined_generic(_TYPE_ALIAS_NS.GenAlias)


T = TypeVar("T", covariant=True)  # make it covariant to use at protocol
V = TypeVar("V")


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


@pytest.mark.parametrize(
    ["tp", "result"],
    [
        (list, bool(HAS_STD_CLASSES_GENERICS)),
        (List, True),
        (Dict, True),
        (List[T], True),
        (List[int], False),
        *cond_list(
            HAS_STD_CLASSES_GENERICS,
            lambda: [
                (list[T], True),
                (list[int], False),
            ],
        ),
        *gen_ns_parametrize(
            lambda gen_ns: (gen_ns.Gen, True),
            lambda gen_ns: (gen_ns.Gen[T], True),
            lambda gen_ns: (gen_ns.Gen[int], False),
        ),
        *cond_list(
            HAS_ANNOTATED,
            lambda: [
                (typing.Annotated, False),
                (typing.Annotated[int, "meta"], False),
                (typing.Annotated[T, "meta"], True),
                (typing.Annotated[list, "meta"], True),
                (typing.Annotated[list[T], "meta"], True),
            ],
        ),
        (type, False),  # cannot be parametrized
        (Type, True),
        *type_alias_ns_parametrize(
            lambda type_alias_ns: (type_alias_ns.IntAlias, False),
            lambda type_alias_ns: (type_alias_ns.RecursiveAlias, False),
            lambda type_alias_ns: (type_alias_ns.GenAlias, True),
            lambda type_alias_ns: (type_alias_ns.GenAlias[int], False),
            lambda type_alias_ns: (type_alias_ns.GenAlias[T], True),
        ),
    ],
)
def test_is_generic(tp, result):
    assert is_generic(tp) == result


@pytest.mark.parametrize(
    ["tp", "result"],
    [
        (list, True),
        (List, True),
        (Dict, True),
        (List[T], False),
        (List[int], False),
        *cond_list(
            HAS_STD_CLASSES_GENERICS,
            lambda: [
                (list[T], False),
                (list[int], False),
            ],
        ),
        *gen_ns_parametrize(
            lambda gen_ns: (gen_ns.Gen, True),
            lambda gen_ns: (gen_ns.Gen[T], False),
            lambda gen_ns: (gen_ns.Gen[int], False),
        ),
        *cond_list(
            HAS_ANNOTATED,
            lambda: [
                (typing.Annotated, False),
                (typing.Annotated[int, "meta"], False),
                (typing.Annotated[T, "meta"], False),
                (typing.Annotated[list, "meta"], False),
                (typing.Annotated[list[T], "meta"], False),
            ],
        ),
        *type_alias_ns_parametrize(
            lambda type_alias_ns: (type_alias_ns.IntAlias, False),
            lambda type_alias_ns: (type_alias_ns.RecursiveAlias, False),
            lambda type_alias_ns: (type_alias_ns.GenAlias, True),
            lambda type_alias_ns: (type_alias_ns.GenAlias[int], False),
            lambda type_alias_ns: (type_alias_ns.GenAlias[T], False),
        ),
    ],
)
def test_is_bare_generic(tp, result):
    assert is_bare_generic(tp) == result


def test_get_type_vars_of_parametrized(gen_ns):  # noqa: PLR0915
    assert get_type_vars_of_parametrized(gen_ns.Gen[T]) == (T,)
    assert get_type_vars_of_parametrized(gen_ns.Gen[str]) == ()
    assert get_type_vars_of_parametrized(gen_ns.Gen) == ()

    assert get_type_vars_of_parametrized(Proto[T]) == (T,)
    assert get_type_vars_of_parametrized(Proto[str]) == ()
    assert get_type_vars_of_parametrized(Proto) == ()

    assert get_type_vars_of_parametrized(list) == ()
    assert get_type_vars_of_parametrized(List[T]) == (T,)
    assert get_type_vars_of_parametrized(List) == ()
    assert get_type_vars_of_parametrized(List[str]) == ()

    assert get_type_vars_of_parametrized(dict) == ()
    assert get_type_vars_of_parametrized(Dict[T, V]) == (T, V)
    assert get_type_vars_of_parametrized(Dict) == ()
    assert get_type_vars_of_parametrized(Dict[str, V]) == (V,)
    assert get_type_vars_of_parametrized(Dict[T, str]) == (T,)
    assert get_type_vars_of_parametrized(Dict[str, str]) == ()
    assert get_type_vars_of_parametrized(Dict[V, T]) == (V, T)

    assert get_type_vars_of_parametrized(tuple) == ()
    assert get_type_vars_of_parametrized(Tuple) == ()
    assert get_type_vars_of_parametrized(Tuple[()]) == ()
    assert get_type_vars_of_parametrized(Tuple[int]) == ()
    assert get_type_vars_of_parametrized(Tuple[int, T]) == (T,)

    assert get_type_vars_of_parametrized(Callable) == ()
    assert get_type_vars_of_parametrized(Callable[..., Any]) == ()
    assert get_type_vars_of_parametrized(Callable[[int], Any]) == ()
    assert get_type_vars_of_parametrized(Callable[[T], Any]) == (T,)
    assert get_type_vars_of_parametrized(Callable[[T], T]) == (T,)
    assert get_type_vars_of_parametrized(Callable[[T, int, V], T]) == (T, V)

    if HAS_STD_CLASSES_GENERICS:
        assert get_type_vars_of_parametrized(list[T]) == (T,)
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
    assert get_type_vars_of_parametrized(Generic[T]) == (T,)
    assert get_type_vars_of_parametrized(Generic[T, V]) == (T, V)

    if HAS_ANNOTATED:
        assert get_type_vars_of_parametrized(typing.Annotated[int, "meta"]) == ()

        assert get_type_vars_of_parametrized(typing.Annotated[list, "meta"]) == ()
        assert get_type_vars_of_parametrized(typing.Annotated[list[int], "meta"]) == ()
        assert get_type_vars_of_parametrized(typing.Annotated[list[T], "meta"]) == (T,)

        assert get_type_vars_of_parametrized(typing.Annotated[gen_ns.Gen, "meta"]) == ()
        assert get_type_vars_of_parametrized(typing.Annotated[gen_ns.Gen[T], "meta"]) == (T,)

        assert get_type_vars_of_parametrized(typing.Annotated[Proto, "meta"]) == ()
        assert get_type_vars_of_parametrized(typing.Annotated[Proto[T], "meta"]) == (T,)


@pytest.mark.parametrize(
    ["cls", "result"],
    [
        (int, False),
        (bool, False),
        (str, False),
        (bytes, False),
        (list, True),
        (dict, True),
        (type, True),
        (set, True),
        (frozenset, True),
        (collections.deque, True),
        (collections.ChainMap, True),
        (collections.defaultdict, True),
        *gen_ns_parametrize(
            lambda gen_ns: (gen_ns.Gen, True),
            lambda gen_ns: (gen_ns.GenChildExplicit, False),
        ),
    ],
)
def test_is_generic_class(cls, result):
    assert is_generic_class(cls) == result


class ListAliasChildGeneric(List):
    pass


class ListAliasChild(List[int]):
    pass


class DictAliasChildGeneric(Dict):
    pass


class DictAliasChild(Dict[str, str]):
    pass


@pytest.mark.parametrize(
    ["cls", "result"],
    [
        (ListAliasChildGeneric, False),
        (ListAliasChild, False),
        (DictAliasChildGeneric, False),
        (DictAliasChild, False),
    ],
)
def test_is_generic_class_builtin_alias_children(cls, result):
    assert is_generic_class(cls) == result


class ListChildGeneric(list):
    pass


class DictChildGeneric(dict):
    pass


def std_classes_parametrized():
    class ListAliasChild(list[int]):
        pass

    class DictAliasChild(dict[str, str]):
        pass

    return [
        (ListAliasChild, False),
        (DictAliasChild, False),
    ]


@pytest.mark.parametrize(
    ["cls", "result"],
    [
        (ListChildGeneric, False),
        (DictChildGeneric, False),
        *cond_list(HAS_STD_CLASSES_GENERICS, std_classes_parametrized),
    ],
)
def test_is_generic_class_builtin_children(cls, result):
    assert is_generic_class(cls) == result
