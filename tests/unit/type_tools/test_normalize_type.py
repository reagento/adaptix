import collections
import re
import typing
from collections import abc as c_abc, defaultdict
from dataclasses import InitVar
from enum import Enum
from itertools import permutations
from types import GenericAlias
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    DefaultDict,
    Dict,
    Final,
    ForwardRef,
    FrozenSet,
    Generic,
    List,
    Literal,
    Match,
    NewType,
    NoReturn,
    Optional,
    Pattern,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import uuid4

import pytest
from tests_helpers import cond_list, full_match, requires

from adaptix._internal.feature_requirement import (
    HAS_PARAM_SPEC,
    HAS_PY_310,
    HAS_PY_311,
    HAS_PY_312,
    HAS_PY_313,
    HAS_TV_DEFAULT,
    HAS_TV_TUPLE,
    HAS_TYPE_ALIAS,
    HAS_TYPE_GUARD,
    HAS_TYPE_UNION_OP,
    HAS_TYPED_DICT_REQUIRED,
)
from adaptix._internal.type_tools import normalize_type
from adaptix._internal.type_tools.normalize_type import (
    AnyNormTypeVarLike,
    Bound,
    Constraints,
    NormParamSpec,
    NormTV,
    NormTVTuple,
    NotSubscribedError,
    _create_norm_literal,
    _NormParamSpecArgs,
    _NormParamSpecKwargs,
    make_norm_type,
)

from .local_helpers import assert_normalize, assert_strict_equal, nt_zero


def test_atomic():
    assert_strict_equal(normalize_type(Any), nt_zero(Any))

    assert_strict_equal(normalize_type(int), nt_zero(int))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(None), nt_zero(None))
    assert_strict_equal(
        normalize_type(type(None)),
        nt_zero(None, source=type(None)),
    )

    assert_strict_equal(normalize_type(object), nt_zero(object))
    assert_strict_equal(normalize_type(NoReturn), nt_zero(NoReturn))


@requires(HAS_PY_311)
def test_never():
    assert_strict_equal(normalize_type(typing.Never), nt_zero(typing.Never))


@requires(HAS_PY_311)
def test_literal_string():
    assert_strict_equal(normalize_type(typing.LiteralString), nt_zero(typing.LiteralString))


@pytest.mark.parametrize(
    ["tp", "alias"],
    [
        (list, List),
        (set, Set),
        (frozenset, FrozenSet),
        (collections.Counter, typing.Counter),
        (collections.deque, typing.Deque),
    ],
)
def test_generic_concrete_one_arg(tp, alias):
    assert_normalize(
        tp,
        tp, [nt_zero(Any)],
    )
    assert_normalize(
        alias,
        tp, [nt_zero(Any)],
    )
    assert_normalize(
        tp[int],
        tp, [nt_zero(int)],
    )
    assert_normalize(
        alias[int],
        tp, [nt_zero(int)],
    )


@pytest.mark.parametrize(
    ["tp", "alias"],
    [
        (dict, Dict),
        (defaultdict, DefaultDict),
        (collections.OrderedDict, typing.OrderedDict),
        (collections.ChainMap, typing.ChainMap),
    ],
)
def test_generic_concrete_two_args(tp, alias):
    assert_normalize(
        tp,
        tp, [nt_zero(Any), nt_zero(Any)],
    )
    assert_normalize(
        alias,
        tp, [nt_zero(Any), nt_zero(Any)],
    )
    assert_normalize(
        tp[int, str],
        tp, [nt_zero(int), nt_zero(str)],
    )
    assert_normalize(
        alias[int, str],
        tp, [nt_zero(int), nt_zero(str)],
    )


def test_special_generics():
    assert_normalize(
        tuple,
        tuple, [nt_zero(Any), ...],
    )
    assert_normalize(
        Tuple,
        tuple, [nt_zero(Any), ...],
    )
    assert_normalize(
        tuple[int],
        tuple, [nt_zero(int)],
    )
    assert_normalize(
        Tuple[int],
        tuple, [nt_zero(int)],
    )
    assert_normalize(
        tuple[int, ...],
        tuple, [nt_zero(int), ...],
    )
    assert_normalize(
        Tuple[int, ...],
        tuple, [nt_zero(int), ...],
    )

    assert_normalize(tuple[()], tuple, [])
    assert_normalize(Tuple[()], tuple, [])

    any_str_placeholder = make_norm_type(
        Union, (nt_zero(bytes), nt_zero(str)), source=Union[bytes, str],
    )

    assert_normalize(Pattern, re.Pattern, [any_str_placeholder])
    assert_normalize(Match, re.Match, [any_str_placeholder])

    assert_normalize(Pattern[bytes], re.Pattern, [nt_zero(bytes)])
    assert_normalize(Match[bytes], re.Match, [nt_zero(bytes)])


@pytest.mark.parametrize(
    "callable_tp",
    [
        Callable,
        c_abc.Callable,
    ],
)
def test_callable(callable_tp):
    assert_normalize(
        callable_tp,
        c_abc.Callable, [..., nt_zero(Any)],
    )
    assert_normalize(
        callable_tp[..., Any],
        c_abc.Callable, [..., nt_zero(Any)],
    )
    assert_normalize(
        callable_tp[..., int],
        c_abc.Callable, [..., nt_zero(int)],
    )
    assert_normalize(
        callable_tp[[str], int],
        c_abc.Callable, [(nt_zero(str),), nt_zero(int)],
    )
    assert_normalize(
        callable_tp[[str, bytes], int],
        c_abc.Callable, [(nt_zero(str), nt_zero(bytes)), nt_zero(int)],
    )

    assert_normalize(
        callable_tp[..., NoReturn],
        c_abc.Callable, [..., nt_zero(NoReturn)],
    )

    hash(normalize_type(callable_tp[..., int]))
    hash(normalize_type(callable_tp[[int, str], int]))


@requires(HAS_TV_TUPLE)
@pytest.mark.parametrize(
    "callable_tp",
    [
        Callable,
        c_abc.Callable,
    ],
)
def test_callable_unpack(callable_tp):
    from typing import TypeVarTuple, Unpack

    assert_normalize(
        callable_tp[[Unpack[Tuple[int]]], Any],
        c_abc.Callable, [(normalize_type(int), ), nt_zero(Any)],
    )
    assert_normalize(
        callable_tp[[Unpack[Tuple[int, str]]], Any],
        c_abc.Callable, [(normalize_type(int), normalize_type(str)), nt_zero(Any)],
    )
    assert_normalize(
        callable_tp[[Unpack[Tuple[int, ...]]], Any],
        c_abc.Callable, [(normalize_type(Unpack[Tuple[int, ...]]), ), nt_zero(Any)],
    )

    t1 = TypeVarTuple("t1")
    assert_normalize(
        callable_tp[[Unpack[t1]], Any],
        c_abc.Callable, [(normalize_type(Unpack[t1]), ), nt_zero(Any)],
    )

    assert_normalize(
        callable_tp[[Unpack[Tuple[()]]], Any],
        c_abc.Callable, [(), nt_zero(Any)],
    )


def test_type(make_union):
    assert_normalize(type, type, [nt_zero(Any)])
    assert_normalize(Type, type, [nt_zero(Any)])

    assert_normalize(Type[int], type, [nt_zero(int)])

    assert_normalize(Type[Any], type, [nt_zero(Any)])

    assert_normalize(
        Type[make_union[int, str]],
        Union, [normalize_type(type[int]), normalize_type(type[str])],
    )

    assert_normalize(
        Union[type[make_union[int, str]], type[int]],
        Union, [normalize_type(type[int]), normalize_type(type[str])],
    )


@pytest.mark.parametrize(
    "tp",
    [
        ClassVar,
        InitVar,
        *cond_list(HAS_TYPE_GUARD, lambda: [typing.TypeGuard]),
        *cond_list(HAS_TYPED_DICT_REQUIRED, lambda: [typing.Required, typing.NotRequired]),
    ],
)
def test_var_tag(tp):
    pytest.raises(NotSubscribedError, lambda: normalize_type(tp))

    assert_normalize(
        tp[int],
        tp, [nt_zero(int)],
    )


@requires(HAS_PY_310)
def test_kw_only():
    from dataclasses import KW_ONLY

    assert_normalize(
        KW_ONLY,
        KW_ONLY, [],
    )


def n_lit(*args):
    return _create_norm_literal(args)


def test_literal(make_union):
    pytest.raises(NotSubscribedError, lambda: normalize_type(Literal))

    assert_normalize(Literal["a"], Literal, ["a"])
    assert_normalize(Literal["a", "b"], Literal, ["a", "b"])
    assert_normalize(Literal[None], None, [])

    assert_normalize(Optional[Literal[None]], None, [])

    assert_strict_equal(
        normalize_type(make_union[Literal[None, "a"], None]),
        make_norm_type(
            Union,
            (nt_zero(None, source=make_union[Literal[None], None]), n_lit("a")),
            source=make_union[Literal[None, "a"], None],
        ),
    )

    assert_normalize(
        make_union[Literal["a"], Literal["b"]],
        Literal, ["a", "b"],
    )

    assert_normalize(
        make_union[Literal["a"], Literal["b"], int],
        Union, [
            n_lit("a", "b"),
            nt_zero(int),
        ],
    )

    assert_normalize(
        make_union[Literal["a"], int, Literal["b"]],
        Union, [
            n_lit("a", "b"),
            nt_zero(int),
        ],
    )

    assert_normalize(
        make_union[int, Literal["a"], Literal["b"]],
        Union, [
            nt_zero(int),
            n_lit("a", "b"),
        ],
    )

    assert make_norm_type(Literal, (0, 1), source=...) != make_norm_type(Literal, (False, True), source=...)
    assert (
        make_norm_type(Literal, (0, 1, False, True), source=...)
        ==
        make_norm_type(Literal, (0, 1, False, True), source=...)
    )


class MyEnum(Enum):
    FOO = 1
    BAR = 2


def test_literal_order(make_union):
    # check that union has a stable args order
    args = ("1", 1, "c", MyEnum.FOO, b"c")

    for p_args in permutations(args):
        assert (
            make_norm_type(Literal, tuple(p_args), source=...)
            ==
            make_norm_type(Literal, args, source=...)
        )

    args_with_rnd = args = (uuid4().hex, )  # prevent Literal caching
    for p_args_with_rnd in permutations(args):
        p_lit = Literal.__getitem__(p_args_with_rnd)
        lit = Literal.__getitem__(args_with_rnd)
        assert_strict_equal(normalize_type(p_lit), normalize_type(lit))


def test_final():
    pytest.raises(NotSubscribedError, lambda: normalize_type(Final))

    assert_normalize(
        Final[int],
        Final, [nt_zero(int)],
    )


def test_annotated():
    pytest.raises(NotSubscribedError, lambda: normalize_type(Annotated))

    assert_normalize(
        Annotated[int, "metadata"],
        Annotated, [nt_zero(int), "metadata"],
    )
    assert_normalize(
        Annotated[int, str],
        Annotated, [nt_zero(int), str],
    )
    assert_normalize(
        Annotated[int, int],
        Annotated, [nt_zero(int), int],
    )

    hash(normalize_type(Annotated[int, "metadata"]))

    class UnHashableMetadata:
        __hash__ = None

    pytest.raises(TypeError, lambda: hash(UnHashableMetadata()))
    hash(normalize_type(Annotated[int, UnHashableMetadata()]))


def test_union(make_union):
    pytest.raises(NotSubscribedError, lambda: normalize_type(Union))

    assert_normalize(
        make_union[int, str],
        Union, [normalize_type(int), normalize_type(str)],
    )

    assert_normalize(
        make_union[list, List, int],
        Union, [normalize_type(Union[list, List]), normalize_type(int)],
    )
    assert_normalize(
        make_union[list, List],
        list, [nt_zero(Any)],
    )
    assert_normalize(
        make_union[list, str, List],
        Union, [normalize_type(Union[list, List]), normalize_type(str)],
    )

    assert_normalize(
        make_union[type[list], type[Union[List, str]]],
        Union, [
            normalize_type(Union[type[list], type[List]]),
            normalize_type(type[str]),
        ],
    )

    # because Union[int] == int normalization does not need


def test_union_order(make_union):
    # check that union has a stable args order
    args = (int, str, bool)

    for p_args in permutations(args):
        assert (
            make_norm_type(Union, tuple(map(normalize_type, p_args)), source=...)
            ==
            make_norm_type(Union, tuple(map(normalize_type, args)), source=...)
        )


def test_optional():
    pytest.raises(NotSubscribedError, lambda: normalize_type(Optional))

    assert_normalize(
        Optional[int],
        Union, [nt_zero(int), nt_zero(None, source=type(None))],
    )

    if HAS_TYPE_UNION_OP:
        assert_normalize(
            int | None,
            Union, [nt_zero(int), nt_zero(None, source=type(None))],
        )

    assert_normalize(
        Optional[None],
        None, [],
    )


def test_new_type():
    with pytest.raises(
        ValueError,
        match=full_match(f"{NewType} must be instantiated"),
    ):
        normalize_type(NewType)

    new_int = NewType("new_int", int)
    assert normalize_type(new_int) == nt_zero(new_int)


def assert_norm_tv(tv: Any, target: AnyNormTypeVarLike):
    assert_strict_equal(
        normalize_type(tv),
        target,
    )


@pytest.mark.parametrize(
    "variance",
    [
        pytest.param({}, id="invariant"),
        pytest.param({"covariant": True}, id="covariant"),
        pytest.param({"contravariant": True}, id="contravariant"),
    ],
)
def test_type_var(variance: dict, make_union):
    t1 = TypeVar("t1", **variance)  # type: ignore[misc]

    assert_norm_tv(
        t1,
        NormTV(t1, limit=Bound(nt_zero(Any)), source=t1, default=None),
    )

    t2 = TypeVar("t2", bound=int, **variance)  # type: ignore[misc]

    assert_norm_tv(
        t2,
        NormTV(t2, limit=Bound(nt_zero(int)), source=t2, default=None),
    )

    t3 = TypeVar("t3", int, str, **variance)  # type: ignore[misc]

    assert_norm_tv(
        t3,
        NormTV(t3, limit=Constraints((nt_zero(int), nt_zero(str))), source=t3, default=None),
    )

    t4 = TypeVar("t4", list, str, List, **variance)  # type: ignore[misc]

    t4_union = normalize_type(make_union[list, List])

    assert_norm_tv(
        t4,
        NormTV(
            t4,
            limit=Constraints(
                (t4_union, nt_zero(str)),
            ),
            source=t4,
            default=None,
        ),
    )

    if HAS_PARAM_SPEC:
        from typing import Concatenate, ParamSpec

        p1 = ParamSpec("p1", **variance)  # type: ignore[misc]

        assert_normalize(
            Concatenate[int, p1],
            Concatenate, [
                nt_zero(int),
                NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None),
            ],
        )

        assert_normalize(
            Concatenate[int, str, p1],
            Concatenate, [
                nt_zero(int),
                nt_zero(str),
                NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None),
            ],
        )

        assert_normalize(
            Callable[Concatenate[int, p1], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None)),
                    source=Concatenate[int, p1],
                ),
                nt_zero(int),
            ],
        )

        assert_normalize(
            Callable[Concatenate[int, str, p1], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (
                        nt_zero(int),
                        nt_zero(str),
                        NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None),
                    ),
                    source=Concatenate[int, str, p1],
                ),
                nt_zero(int),
            ],
        )

        p2 = ParamSpec("p2", bound=str)  # type: ignore[misc]
        assert_norm_tv(
            p2,
            NormParamSpec(p2, limit=Bound(nt_zero(str)), source=p2, default=None),
        )

        assert_normalize(
            Callable[Concatenate[int, p2], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), NormParamSpec(p2, limit=Bound(nt_zero(str)), source=p2, default=None)),
                    source=Concatenate[int, p2],
                ),
                nt_zero(int),
            ],
        )

        assert_normalize(
            Callable[Concatenate[int, str, p2], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (
                        nt_zero(int),
                        nt_zero(str),
                        NormParamSpec(p2, limit=Bound(nt_zero(str)), source=p2, default=None),
                    ),
                    source=Concatenate[int, str, p2],
                ),
                nt_zero(int),
            ],
        )


# make it covariant to use at protocol
K = TypeVar("K", covariant=True)
V = TypeVar("V", covariant=True)
H = TypeVar("H", int, str, covariant=True)


class MyGeneric1(Generic[K]):
    pass


class MyGeneric2(Generic[K, V]):
    pass


class MyGeneric3(MyGeneric1[K], Generic[K, V, H]):
    pass


class MyProtocol1(Protocol[K]):
    pass


class MyProtocol2(Protocol[K, V]):
    pass


class MyProtocol3(MyProtocol1[K], Protocol[K, V, H]):
    pass


T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")


def any_tv(tv: Any):
    return NormTV(tv, Bound(nt_zero(Any)), source=tv, default=None)


def test_generic(make_union):
    gen: Any

    for gen in [MyGeneric1, MyProtocol1]:
        assert_normalize(gen, gen, [nt_zero(Any)])
        assert_normalize(gen[int], gen, [nt_zero(int)])
        assert_normalize(gen[T1], gen, [any_tv(T1)])

    for gen in [MyGeneric2, MyProtocol2]:
        assert_normalize(gen, gen, [nt_zero(Any), nt_zero(Any)])
        assert_normalize(gen[int, str], gen, [nt_zero(int), nt_zero(str)])
        assert_normalize(gen[T1, T2], gen, [any_tv(T1), any_tv(T2)])
        assert_normalize(gen[T1, T1], gen, [any_tv(T1), any_tv(T1)])

    h_implicit = normalize_type(make_union[int, str])

    for gen in [MyGeneric3, MyProtocol3]:
        assert_normalize(gen, gen, [nt_zero(Any), nt_zero(Any), h_implicit])
        assert_normalize(gen[int, str, bool], gen, [nt_zero(int), nt_zero(str), nt_zero(bool)])
        assert_normalize(gen[T1, T2, T3], gen, [any_tv(T1), any_tv(T2), any_tv(T3)])
        assert_normalize(gen[T1, T1, T1], gen, [any_tv(T1), any_tv(T1), any_tv(T1)])


def any_ps(tv: Any):
    return NormParamSpec(tv, Bound(nt_zero(Any)), source=tv, default=None)


@requires(HAS_PARAM_SPEC)
def test_generic_and_protocol_with_param_spec():
    from typing import Concatenate, ParamSpec

    p1 = ParamSpec("p1")
    p2 = ParamSpec("p2")
    p3 = ParamSpec("p3")
    t1 = TypeVar("t1", covariant=True)

    class MyGen1(Generic[p1]):
        pass

    class MyGen2(Generic[p1, t1, p2]):
        pass

    class MyProto1(Protocol[p1]):
        pass

    class MyProto2(Protocol[p1, t1, p2]):
        pass

    gen: Any

    for gen in [MyGen1, MyProto1]:
        assert_normalize(gen, gen, [...])
        assert_normalize(gen[...], gen, [...])
        assert_normalize(gen[int], gen, [(nt_zero(int),)])
        assert_normalize(gen[[int]], gen, [(nt_zero(int),)])
        assert_normalize(gen[int, str], gen, [(nt_zero(int), nt_zero(str))])
        assert_normalize(gen[[int, str]], gen, [(nt_zero(int), nt_zero(str))])
        assert_normalize(gen[p3], gen, [any_ps(p3)])
        assert_normalize(
            gen[Concatenate[int, p3]],
            gen, [make_norm_type(Concatenate, (nt_zero(int), any_ps(p3)), source=Concatenate[int, p3])],
        )

    for gen in [MyGen2, MyProto2]:
        assert_normalize(gen, gen, [..., nt_zero(Any), ...])
        assert_normalize(gen[..., Any, ...], gen, [..., nt_zero(Any), ...])
        assert_normalize(
            gen[[int], str, [int]],
            gen, [(nt_zero(int),), nt_zero(str), (nt_zero(int),)],
        )
        assert_normalize(
            gen[[int, str], str, [int, str]],
            gen, [(nt_zero(int), nt_zero(str)), nt_zero(str), (nt_zero(int), nt_zero(str))],
        )
        assert_normalize(
            gen[p3, str, p3],
            gen, [any_ps(p3), nt_zero(str), any_ps(p3)],
        )
        assert_normalize(
            gen[p3, T3, p3],
            gen, [any_ps(p3), any_tv(T3), any_ps(p3)],
        )
        assert_normalize(
            gen[Concatenate[int, p3], str, Concatenate[bool, p3]],
            gen, [
                make_norm_type(Concatenate, (nt_zero(int), any_ps(p3)), source=Concatenate[int, p3]),
                nt_zero(str),
                make_norm_type(Concatenate, (nt_zero(bool), any_ps(p3)), source=Concatenate[bool, p3]),
            ],
        )


T_FR1 = TypeVar("T_FR1", bound="int")
T_FR2 = TypeVar("T_FR2", bound="MyForwardClass")
T_FR3 = TypeVar("T_FR3", bound=List["MyForwardClass"])
T_FR4 = TypeVar("T_FR4", "MyForwardClass", "MyAnotherForwardClass")


class MyForwardClass:
    pass


class MyAnotherForwardClass:
    pass


if HAS_PARAM_SPEC:
    P_FR1 = typing.ParamSpec("P_FR1", bound="int")  # type: ignore[misc]
    P_FR2 = typing.ParamSpec("P_FR2", bound="MyForwardClass")  # type: ignore[misc]
    P_FR3 = typing.ParamSpec("P_FR3", bound=List["MyForwardClass"])  # type: ignore[misc]


def test_forward_ref_at_type_var_limit():
    constraint_source = str if HAS_PY_312 else ForwardRef

    assert_norm_tv(
        T_FR1,
        NormTV(
            T_FR1,
            limit=Bound(nt_zero(int, source=ForwardRef("int"))),
            source=T_FR1,
            default=None,
        ),
    )
    assert_norm_tv(
        T_FR2,
        NormTV(
            T_FR2,
            limit=Bound(nt_zero(MyForwardClass, source=ForwardRef("MyForwardClass"))),
            source=T_FR2,
            default=None,
        ),
    )
    assert_norm_tv(
        T_FR3,
        NormTV(
            T_FR3,
            limit=Bound(
                make_norm_type(
                    list,
                    (nt_zero(MyForwardClass, source=ForwardRef("MyForwardClass")),),
                    source=List[ForwardRef("MyForwardClass")],
                ),
            ),
            source=T_FR3,
            default=None,
        ),
    )
    assert_norm_tv(
        T_FR4,
        NormTV(
            T_FR4,
            limit=Constraints(
                (
                    make_norm_type(MyForwardClass, (), source=constraint_source("MyForwardClass")),
                    make_norm_type(MyAnotherForwardClass, (), source=constraint_source("MyAnotherForwardClass")),
                ),
            ),
            source=T_FR4,
            default=None,
        ),
    )

    if HAS_PARAM_SPEC:
        assert_norm_tv(
            P_FR1,
            NormParamSpec(
                P_FR1,
                limit=Bound(nt_zero(int, source=ForwardRef("int"))),
                source=P_FR1,
                default=None,
            ),
        )
        assert_norm_tv(
            P_FR2,
            NormParamSpec(
                P_FR2,
                limit=Bound(nt_zero(MyForwardClass, source=ForwardRef("MyForwardClass"))),
                source=P_FR2,
                default=None,
            ),
        )
        assert_norm_tv(
            P_FR3,
            NormParamSpec(
                P_FR3,
                limit=Bound(
                    make_norm_type(
                        list,
                        (nt_zero(MyForwardClass, source=ForwardRef("MyForwardClass")),),
                        source=List[ForwardRef("MyForwardClass")],
                    ),
                ),
                source=P_FR3,
                default=None,
            ),
        )


@requires(HAS_PARAM_SPEC)
def test_param_spec_args_and_kwargs():
    from typing import ParamSpec, ParamSpecArgs, ParamSpecKwargs

    p1 = ParamSpec("p1")

    assert_strict_equal(
        normalize_type(p1.args),
        _NormParamSpecArgs(NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None), source=p1.args),
    )

    assert normalize_type(p1.args).origin == ParamSpecArgs

    assert_strict_equal(
        normalize_type(p1.kwargs),
        _NormParamSpecKwargs(NormParamSpec(p1, limit=Bound(nt_zero(Any)), source=p1, default=None), source=p1.kwargs),
    )

    assert normalize_type(p1.kwargs).origin == ParamSpecKwargs


def test_bad_arg_types():
    with pytest.raises(ValueError, match=full_match(f"Cannot normalize value {100!r}")):
        normalize_type(100)

    with pytest.raises(
        ValueError,
        match=full_match("Cannot normalize value 'string', there are no namespace to evaluate types"),
    ):
        normalize_type("string")

    with pytest.raises(ValueError, match=full_match(f"{TypeVar!r} must be instantiated")):
        normalize_type(TypeVar)


class UserClass:
    pass


def test_user_class():
    assert_normalize(
        UserClass,
        UserClass, [],
    )


@requires(HAS_TYPE_ALIAS)
def test_type_alias():
    assert_normalize(
        typing.TypeAlias,
        typing.TypeAlias, [],
    )


def test_types_generic_alias():
    assert_normalize(
        GenericAlias(list, (int,)),
        list, [nt_zero(int)],
    )

    assert_normalize(
        GenericAlias(dict, (str, int)),
        dict, [nt_zero(str), nt_zero(int)],
    )

    assert_normalize(
        GenericAlias,
        GenericAlias, [],
    )


@requires(HAS_TV_TUPLE)
def test_unpack():
    from typing import TypeVarTuple, Unpack

    assert_normalize(
        Unpack[Tuple[int]],
        Unpack, [normalize_type(Tuple[int])],
    )
    assert_normalize(
        Unpack[Tuple[int, ...]],
        Unpack, [normalize_type(Tuple[int, ...])],
    )
    assert_normalize(
        Unpack[Tuple[int, str]],
        Unpack, [normalize_type(Tuple[int, str])],
    )

    t1 = TypeVarTuple("t1")
    assert_normalize(
        Unpack[t1],
        Unpack, [normalize_type(t1)],
    )

    assert_normalize(
        Tuple[Unpack[Tuple[int, str]]],
        tuple, [nt_zero(int), nt_zero(str)],
    )
    assert_normalize(
        Tuple[Unpack[Tuple[int, ...]]],
        tuple, [nt_zero(int), ...],
    )
    assert_normalize(
        Tuple[str, Unpack[Tuple[int, str]], bool],
        tuple, [nt_zero(str), nt_zero(int), nt_zero(str), nt_zero(bool)],
    )
    assert_normalize(
        Tuple[Unpack[Tuple[int, str]], Unpack[Tuple[int, str]]],
        tuple, [nt_zero(int), nt_zero(str), nt_zero(int), nt_zero(str)],
    )

    assert_normalize(
        Tuple[str, Unpack[Tuple[int, Unpack[Tuple[bool]], str]], bool],
        tuple, [nt_zero(str), nt_zero(int), nt_zero(bool), nt_zero(str), nt_zero(bool)],
    )
    assert_normalize(
        Tuple[str, Unpack[Tuple[int, Unpack[Tuple[bool, ...]], str]], bool],
        tuple, [nt_zero(str), nt_zero(int), normalize_type(Unpack[Tuple[bool, ...]]), nt_zero(str), nt_zero(bool)],
    )

    assert_normalize(
        Tuple[Unpack[Tuple[()]]],
        tuple, [],
    )
    assert_normalize(
        Tuple[int, Unpack[Tuple[()]]],
        tuple, [nt_zero(int)],
    )
    assert_normalize(
        Tuple[int, Unpack[Tuple[()]], str],
        tuple, [nt_zero(int), nt_zero(str)],
    )


@requires(HAS_TV_TUPLE)
def test_type_var_tuple():
    from typing import TypeVarTuple

    t1 = TypeVarTuple("t1")
    assert_norm_tv(t1, NormTVTuple(t1, source=t1, default=None))


@requires(HAS_TV_TUPLE)
@pytest.mark.parametrize("tpl", [tuple, Tuple])
def test_type_var_tuple_generic(tpl):
    from typing import TypeVarTuple, Unpack

    ShapeT = TypeVarTuple("ShapeT")

    class Array(Generic[Unpack[ShapeT]]):
        pass

    assert_normalize(
        Array,
        Array, [normalize_type(Unpack[tuple[Any, ...]])],
    )
    assert_normalize(
        Array[int],
        Array, [nt_zero(int)],
    )
    assert_normalize(
        Array[int, str],
        Array, [nt_zero(int), nt_zero(str)],
    )

    assert_normalize(
        Array[int, Unpack[tpl[str, bool]]],
        Array, [nt_zero(int), nt_zero(str), nt_zero(bool)],
    )
    assert_normalize(
        Array[int, Unpack[tpl[()]]],
        Array, [nt_zero(int)],
    )


@requires(HAS_TV_TUPLE)
@pytest.mark.parametrize("tpl", [tuple, Tuple])
def test_type_var_tuple_generic_pre(tpl):
    from typing import TypeVarTuple, Unpack

    ShapeT = TypeVarTuple("ShapeT")
    DType = TypeVar("DType")

    class PreArray(Generic[DType, Unpack[ShapeT]]):
        pass

    assert_normalize(
        PreArray,
        PreArray, [nt_zero(Any), normalize_type(Unpack[tuple[Any, ...]])],
    )
    assert_normalize(
        PreArray[int],
        PreArray, [nt_zero(int)],
    )
    assert_normalize(
        PreArray[int, str],
        PreArray, [nt_zero(int), nt_zero(str)],
    )
    assert_normalize(
        PreArray[int, Unpack[tpl[str]]],
        PreArray, [nt_zero(int), nt_zero(str)],
    )
    assert_normalize(
        PreArray[int, Unpack[tpl[str, bool]]],
        PreArray, [nt_zero(int), nt_zero(str), nt_zero(bool)],
    )
    assert_normalize(
        PreArray[int, Unpack[tpl[()]]],
        PreArray, [nt_zero(int)],
    )


@requires(HAS_TV_TUPLE)
@pytest.mark.parametrize("tpl", [tuple, Tuple])
def test_type_var_tuple_generic_post(tpl):
    from typing import TypeVarTuple, Unpack

    ShapeT = TypeVarTuple("ShapeT")
    DType = TypeVar("DType")

    class PostArray(Generic[Unpack[ShapeT], DType]):
        pass

    assert_normalize(
        PostArray,
        PostArray, [normalize_type(Unpack[tuple[Any, ...]]), nt_zero(Any)],
    )
    assert_normalize(
        PostArray[int],
        PostArray, [nt_zero(int)],
    )
    assert_normalize(
        PostArray[int, str],
        PostArray, [nt_zero(int), nt_zero(str)],
    )
    assert_normalize(
        PostArray[Unpack[tpl[()]], int],
        PostArray, [nt_zero(int)],
    )


@requires(HAS_PY_313)
def test_read_only():
    from typing import ReadOnly

    assert_normalize(
        ReadOnly[int],
        ReadOnly, [normalize_type(int)],
    )

    with pytest.raises(ValueError, match=full_match(f"{ReadOnly!r} must be subscribed")):
        normalize_type(ReadOnly)


@requires(HAS_PY_313)
def test_type_is():
    from typing import TypeIs

    assert_normalize(
        TypeIs[int],
        TypeIs, [normalize_type(int)],
    )

    with pytest.raises(ValueError, match=full_match(f"{TypeIs!r} must be subscribed")):
        normalize_type(TypeIs)


@requires(HAS_TV_DEFAULT)
def test_type_var_default():
    from typing import NoDefault

    tv1 = TypeVar("tv1", default=int)
    assert_norm_tv(
        tv1,
        NormTV(tv1, Bound(nt_zero(Any)), source=tv1, default=normalize_type(int)),
    )
    tv2 = TypeVar("tv2", default=None)
    assert_norm_tv(
        tv2,
        NormTV(tv2, Bound(nt_zero(Any)), source=tv2, default=normalize_type(None)),
    )
    tv3 = TypeVar("tv3", default=NoDefault)
    assert_norm_tv(
        tv3,
        NormTV(tv3, Bound(nt_zero(Any)), source=tv3, default=None),
    )
    tv4 = TypeVar("tv4")
    assert_norm_tv(
        tv4,
        NormTV(tv4, Bound(nt_zero(Any)), source=tv4, default=None),
    )


@requires(HAS_TV_DEFAULT)
def test_type_var_tuple_default():
    from typing import NoDefault, TypeVarTuple

    tvt1 = TypeVarTuple("tvt1", default=(int, ))
    assert_norm_tv(
        tvt1,
        NormTVTuple(tvt1, source=tvt1, default=(normalize_type(int), )),
    )
    tvt2 = TypeVarTuple("tvt2", default=(int, str))
    assert_norm_tv(
        tvt2,
        NormTVTuple(tvt2, source=tvt2, default=(normalize_type(int), normalize_type(str))),
    )
    tvt3 = TypeVarTuple("tvt3", default=(None, ))
    assert_norm_tv(
        tvt3,
        NormTVTuple(tvt3, source=tvt3, default=(normalize_type(None), )),
    )
    tvt4 = TypeVarTuple("tvt4", default=NoDefault)
    assert_norm_tv(
        tvt4,
        NormTVTuple(tvt4, source=tvt4, default=None),
    )
    tvt5 = TypeVarTuple("tvt5")
    assert_norm_tv(
        tvt5,
        NormTVTuple(tvt5, source=tvt5, default=None),
    )


@requires(HAS_TV_DEFAULT)
def test_param_spec_default():
    from typing import NoDefault, ParamSpec

    ps1 = ParamSpec("ps1", default=(int, ))
    assert_norm_tv(
        ps1,
        NormParamSpec(ps1, Bound(nt_zero(Any)), source=ps1, default=(normalize_type(int), )),
    )
    ps2 = ParamSpec("ps2", default=(int, str))
    assert_norm_tv(
        ps2,
        NormParamSpec(ps2, Bound(nt_zero(Any)), source=ps2, default=(normalize_type(int), normalize_type(str))),
    )
    ps3 = ParamSpec("ps3", default=(None, ))
    assert_norm_tv(
        ps3,
        NormParamSpec(ps3, Bound(nt_zero(Any)), source=ps3, default=(normalize_type(None), )),
    )
    ps4 = ParamSpec("ps4", default=NoDefault)
    assert_norm_tv(
        ps4,
        NormParamSpec(ps4, Bound(nt_zero(Any)), source=ps4, default=None),
    )
    ps5 = ParamSpec("ps5")
    assert_norm_tv(
        ps5,
        NormParamSpec(ps5, Bound(nt_zero(Any)), source=ps5, default=None),
    )
