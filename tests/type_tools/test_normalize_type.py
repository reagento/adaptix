import collections
import operator
import re
import typing
from collections import abc as c_abc, defaultdict
from dataclasses import InitVar
from enum import Enum
from functools import reduce
from itertools import permutations
from typing import (
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
    cast,
)
from uuid import uuid4

import pytest

from adaptix import TypeHint
from adaptix._internal.feature_requirement import (
    HAS_ANNOTATED,
    HAS_PARAM_SPEC,
    HAS_STD_CLASSES_GENERICS,
    HAS_TYPE_ALIAS,
    HAS_TYPE_GUARD,
    HAS_TYPE_UNION_OP,
)
from adaptix._internal.type_tools import normalize_type
from adaptix._internal.type_tools.normalize_type import (
    BaseNormType,
    Bound,
    Constraints,
    NormParamSpecMarker,
    NormTV,
    NotSubscribedError,
    _create_norm_literal,
    _NormParamSpecArgs,
    _NormParamSpecKwargs,
    _NormType,
    make_norm_type,
)
from tests_helpers import requires

MISSING = object()


def nt_zero(origin, source=MISSING):
    if source is MISSING:
        source = origin
    return _NormType(origin, (), source=source)


def _norm_to_dict(obj):
    if isinstance(obj, NormTV):
        return {
            'variance': obj.variance,
            'limit': (
                _norm_to_dict(obj.limit.value)
                if isinstance(obj.limit, Bound) else
                [_norm_to_dict(el) for el in obj.limit.value]
            ),
            'source': obj.source,
        }
    if isinstance(obj, NormParamSpecMarker):
        return {
            'origin': obj.origin,
            'param_spec': obj.param_spec,
        }
    if isinstance(obj, BaseNormType):
        result = {
            'origin': obj.origin,
            'args': [_norm_to_dict(arg) for arg in obj.args],
            'source': obj.source,
        }
        if obj.origin == Union:
            result.pop('source')
        return result
    return obj


def assert_strict_equal(left: BaseNormType, right: BaseNormType):
    assert _norm_to_dict(left) == _norm_to_dict(right)
    assert left == right
    hash(left)
    hash(right)


def assert_normalize(tp: TypeHint, origin: TypeHint, args: List[typing.Hashable]):
    assert_strict_equal(
        normalize_type(tp),
        make_norm_type(origin, tuple(args), source=tp)
    )


class UnionOpMaker:
    __name__ = 'UnionOp'  # for test id generation

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return reduce(operator.or_, item)
        return item


@pytest.fixture(params=[Union, UnionOpMaker()] if HAS_TYPE_UNION_OP else [Union])
def make_union(request):
    return request.param


def test_atomic():
    assert_strict_equal(normalize_type(Any), nt_zero(Any))

    assert_strict_equal(normalize_type(int), nt_zero(int))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(None), nt_zero(None))
    assert_strict_equal(
        normalize_type(type(None)),
        nt_zero(None, source=type(None))
    )

    assert_strict_equal(normalize_type(object), nt_zero(object))
    assert_strict_equal(normalize_type(NoReturn), nt_zero(NoReturn))


@pytest.mark.parametrize(
    ['tp', 'alias'],
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
        tp, [nt_zero(Any)]
    )
    assert_normalize(
        alias,
        tp, [nt_zero(Any)]
    )
    if HAS_STD_CLASSES_GENERICS:
        assert_normalize(
            tp[int],
            tp, [nt_zero(int)]
        )
    assert_normalize(
        alias[int],
        tp, [nt_zero(int)]
    )


@pytest.mark.parametrize(
    ['tp', 'alias'],
    [
        (dict, Dict),
        (defaultdict, DefaultDict),
        (collections.OrderedDict, typing.OrderedDict),
        (collections.ChainMap, typing.ChainMap),
    ]
)
def test_generic_concrete_two_args(tp, alias):
    assert_normalize(
        tp,
        tp, [nt_zero(Any), nt_zero(Any)]
    )
    assert_normalize(
        alias,
        tp, [nt_zero(Any), nt_zero(Any)]
    )
    if HAS_STD_CLASSES_GENERICS:
        assert_normalize(
            tp[int, str],
            tp, [nt_zero(int), nt_zero(str)]
        )
    assert_normalize(
        alias[int, str],
        tp, [nt_zero(int), nt_zero(str)]
    )


def test_special_generics():
    assert_normalize(
        tuple,
        tuple, [nt_zero(Any), ...]
    )
    assert_normalize(
        Tuple,
        tuple, [nt_zero(Any), ...]
    )
    if HAS_STD_CLASSES_GENERICS:
        assert_normalize(
            tuple[int],
            tuple, [nt_zero(int)]
        )
    assert_normalize(
        Tuple[int],
        tuple, [nt_zero(int)]
    )
    if HAS_STD_CLASSES_GENERICS:
        assert_normalize(
            tuple[int, ...],
            tuple, [nt_zero(int), ...]
        )
    assert_normalize(
        Tuple[int, ...],
        tuple, [nt_zero(int), ...]
    )

    if HAS_STD_CLASSES_GENERICS:
        assert_normalize(tuple[()], tuple, [])
    assert_normalize(Tuple[()], tuple, [])

    any_str_placeholder = make_norm_type(
        Union, (nt_zero(bytes), nt_zero(str)), source=Union[bytes, str]
    )

    assert_normalize(Pattern, re.Pattern, [any_str_placeholder])
    assert_normalize(Match, re.Match, [any_str_placeholder])

    assert_normalize(Pattern[bytes], re.Pattern, [nt_zero(bytes)])
    assert_normalize(Match[bytes], re.Match, [nt_zero(bytes)])


def test_callable():
    assert_normalize(
        Callable,
        c_abc.Callable, [..., nt_zero(Any)],
    )
    assert_normalize(
        Callable[..., Any],
        c_abc.Callable, [..., nt_zero(Any)],
    )
    assert_normalize(
        Callable[..., int],
        c_abc.Callable, [..., nt_zero(int)],
    )
    assert_normalize(
        Callable[[str], int],
        c_abc.Callable, [(nt_zero(str),), nt_zero(int)],
    )
    assert_normalize(
        Callable[[str, bytes], int],
        c_abc.Callable, [(nt_zero(str), nt_zero(bytes)), nt_zero(int)],
    )

    assert_normalize(
        Callable[..., NoReturn],
        c_abc.Callable, [..., nt_zero(NoReturn)],
    )

    hash(normalize_type(Callable[..., int]))
    hash(normalize_type(Callable[[int, str], int]))


def test_type(make_union):
    assert_normalize(type, type, [nt_zero(Any)])
    assert_normalize(Type, type, [nt_zero(Any)])

    assert_normalize(Type[int], type, [nt_zero(int)])

    assert_normalize(Type[Any], type, [nt_zero(Any)])

    assert_normalize(
        Type[make_union[int, str]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str])]
    )

    assert_normalize(
        Union[Type[make_union[int, str]], Type[bool]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str]), normalize_type(Type[bool])]
    )

    assert_normalize(
        Union[Type[make_union[int, str]], Type[int]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str])]
    )


VAR_TAGS = [ClassVar, InitVar]

if HAS_TYPE_GUARD:
    VAR_TAGS.append(typing.TypeGuard)


@pytest.mark.parametrize('tp', VAR_TAGS)
def test_var_tag(tp):
    pytest.raises(NotSubscribedError, lambda: normalize_type(tp))

    assert_normalize(
        tp[int],
        tp, [nt_zero(int)]
    )


def n_lit(*args):
    return _create_norm_literal(args)


def test_literal(make_union):
    pytest.raises(NotSubscribedError, lambda: normalize_type(Literal))

    assert_normalize(Literal['a'], Literal, ['a'])
    assert_normalize(Literal['a', 'b'], Literal, ['a', 'b'])
    assert_normalize(Literal[None], None, [])

    assert_normalize(Optional[Literal[None]], None, [])

    assert_strict_equal(
        normalize_type(make_union[Literal[None, 'a'], None]),
        make_norm_type(
            Union,
            (nt_zero(None, source=make_union[Literal[None], None]), n_lit('a')),
            source=make_union[Literal[None, 'a'], None]
        )
    )

    assert_normalize(
        make_union[Literal['a'], Literal['b']],
        Literal, ['a', 'b']
    )

    assert_normalize(
        make_union[Literal['a'], Literal['b'], int],
        Union, [
            n_lit('a', 'b'),
            nt_zero(int)
        ]
    )

    assert_normalize(
        make_union[Literal['a'], int, Literal['b']],
        Union, [
            n_lit('a', 'b'),
            nt_zero(int),
        ]
    )

    assert_normalize(
        make_union[int, Literal['a'], Literal['b']],
        Union, [
            nt_zero(int),
            n_lit('a', 'b'),
        ]
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
    # check that union has stable args order
    args = ('1', 1, 'c', MyEnum.FOO, b'c')

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
        Final, [nt_zero(int)]
    )


@requires(HAS_ANNOTATED)
def test_annotated():
    from typing import Annotated

    pytest.raises(NotSubscribedError, lambda: normalize_type(Annotated))

    assert_normalize(
        Annotated[int, 'metadata'],
        Annotated, [nt_zero(int), 'metadata']
    )
    assert_normalize(
        Annotated[int, str],
        Annotated, [nt_zero(int), str]
    )
    assert_normalize(
        Annotated[int, int],
        Annotated, [nt_zero(int), int]
    )

    hash(normalize_type(Annotated[int, 'metadata']))

    class UnHashableMetadata:
        __hash__ = None

    pytest.raises(TypeError, lambda: hash(UnHashableMetadata()))
    hash(normalize_type(Annotated[int, UnHashableMetadata()]))


def test_union(make_union):
    pytest.raises(NotSubscribedError, lambda: normalize_type(Union))

    assert_normalize(
        make_union[int, str],
        Union, [normalize_type(int), normalize_type(str)]
    )

    assert_normalize(
        make_union[list, List, int],
        Union, [normalize_type(Union[list, List]), normalize_type(int)]
    )
    assert_normalize(
        make_union[list, List],
        list, [nt_zero(Any)]
    )
    assert_normalize(
        make_union[list, str, List],
        Union, [normalize_type(Union[list, List]), normalize_type(str)]
    )

    assert_normalize(
        make_union[Type[list], Type[Union[List, str]]],
        Union, [
            normalize_type(Union[Type[list], Type[List]]),
            normalize_type(Type[str])
        ]
    )

    # because Union[int] == int   # normalization does not need


def test_union_order(make_union):
    # check that union has stable args order
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
        Union, [nt_zero(int), nt_zero(None, source=type(None))]
    )

    if HAS_TYPE_UNION_OP:
        assert_normalize(
            int | None,
            Union, [nt_zero(int), nt_zero(None, source=type(None))]
        )

    assert_normalize(
        Optional[None],
        None, []
    )


def test_new_type():
    pytest.raises(ValueError, lambda: normalize_type(NewType))

    new_int = NewType('new_int', int)
    assert normalize_type(new_int) == nt_zero(new_int)


def assert_norm_tv(tv: Any, target: NormTV):
    assert_strict_equal(
        normalize_type(tv),
        target
    )


@pytest.mark.parametrize(
    'variance',
    [
        pytest.param({}, id="invariant"),
        pytest.param({'covariant': True}, id='covariant'),
        pytest.param({'contravariant': True}, id='contravariant'),
    ],
)
def test_type_var(variance: dict, make_union):
    t1 = TypeVar("t1", **variance)  # type: ignore[misc]

    assert_norm_tv(
        t1,
        NormTV(t1, limit=Bound(nt_zero(Any)), source=t1)
    )

    t2 = TypeVar("t2", bound=int, **variance)  # type: ignore[misc]

    assert_norm_tv(
        t2,
        NormTV(t2, limit=Bound(nt_zero(int)), source=t2)
    )

    t3 = TypeVar("t3", int, str, **variance)  # type: ignore[misc]

    assert_norm_tv(
        t3,
        NormTV(t3, limit=Constraints((nt_zero(int), nt_zero(str))), source=t3)
    )

    t4 = TypeVar("t4", list, str, List, **variance)  # type: ignore[misc]

    t4_union = cast(_NormType, normalize_type(make_union[list, List]))

    assert_norm_tv(
        t4,
        NormTV(
            t4,
            limit=Constraints(
                (t4_union, nt_zero(str))
            ),
            source=t4,
        )
    )

    if HAS_PARAM_SPEC:
        from typing import Concatenate, ParamSpec

        p1 = ParamSpec('p1', **variance)  # type: ignore[misc]

        assert_normalize(
            Concatenate[int, p1],
            Concatenate, [nt_zero(int), NormTV(p1, limit=Bound(nt_zero(Any)), source=p1)],
        )

        assert_normalize(
            Concatenate[int, str, p1],
            Concatenate, [nt_zero(int), nt_zero(str), NormTV(p1, limit=Bound(nt_zero(Any)), source=p1)],
        )

        assert_normalize(
            Callable[Concatenate[int, p1], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), NormTV(p1, limit=Bound(nt_zero(Any)), source=p1)),
                    source=Concatenate[int, p1]
                ),
                nt_zero(int),
            ],
        )

        assert_normalize(
            Callable[Concatenate[int, str, p1], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), nt_zero(str), NormTV(p1, limit=Bound(nt_zero(Any)), source=p1)),
                    source=Concatenate[int, str, p1]
                ),
                nt_zero(int),
            ],
        )

        p2 = ParamSpec('p2', bound=str)  # type: ignore[misc]
        assert_norm_tv(
            p2,
            NormTV(p2, limit=Bound(nt_zero(str)), source=p2)
        )

        assert_normalize(
            Callable[Concatenate[int, p2], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), NormTV(p2, limit=Bound(nt_zero(str)), source=p2)),
                    source=Concatenate[int, p2]
                ),
                nt_zero(int),
            ],
        )

        assert_normalize(
            Callable[Concatenate[int, str, p2], int],
            c_abc.Callable, [
                make_norm_type(
                    Concatenate,
                    (nt_zero(int), nt_zero(str), NormTV(p2, limit=Bound(nt_zero(str)), source=p2)),
                    source=Concatenate[int, str, p2]
                ),
                nt_zero(int),
            ],
        )


# make it covariant to use at protocol
K = TypeVar('K', covariant=True)
V = TypeVar('V', covariant=True)
H = TypeVar('H', int, str, covariant=True)


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


T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')


def any_tv(tv: Any):
    return NormTV(tv, Bound(nt_zero(Any)), source=tv)


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


@requires(HAS_PARAM_SPEC)
def test_generic_and_protocol_with_param_spec():
    from typing import Concatenate, ParamSpec

    p1 = ParamSpec('p1')
    p2 = ParamSpec('p2')
    p3 = ParamSpec('p3')
    t1 = TypeVar('t1', covariant=True)

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
        assert_normalize(gen[int], gen, [(nt_zero(int), )])
        assert_normalize(gen[[int]], gen, [(nt_zero(int), )])
        assert_normalize(gen[int, str], gen, [(nt_zero(int), nt_zero(str))])
        assert_normalize(gen[[int, str]], gen, [(nt_zero(int), nt_zero(str))])
        assert_normalize(gen[p3], gen, [any_tv(p3)])
        assert_normalize(
            gen[Concatenate[int, p3]],
            gen, [make_norm_type(Concatenate, (nt_zero(int), any_tv(p3)), source=Concatenate[int, p3])]
        )

    for gen in [MyGen2, MyProto2]:
        assert_normalize(gen, gen, [..., nt_zero(Any), ...])
        assert_normalize(gen[..., Any, ...], gen, [..., nt_zero(Any), ...])
        assert_normalize(
            gen[[int], str, [int]],
            gen, [(nt_zero(int), ), nt_zero(str), (nt_zero(int), )]
        )
        assert_normalize(
            gen[[int, str], str, [int, str]],
            gen, [(nt_zero(int), nt_zero(str)), nt_zero(str), (nt_zero(int), nt_zero(str))]
        )
        assert_normalize(
            gen[p3, str, p3],
            gen, [any_tv(p3), nt_zero(str), any_tv(p3)]
        )
        assert_normalize(
            gen[p3, T3, p3],
            gen, [any_tv(p3), any_tv(T3), any_tv(p3)]
        )
        assert_normalize(
            gen[Concatenate[int, p3], str, Concatenate[bool, p3]],
            gen, [
                make_norm_type(Concatenate, (nt_zero(int), any_tv(p3)), source=Concatenate[int, p3]),
                nt_zero(str),
                make_norm_type(Concatenate, (nt_zero(bool), any_tv(p3)), source=Concatenate[bool, p3]),
            ]
        )


T_FR1 = TypeVar('T_FR1', bound='int')
T_FR2 = TypeVar('T_FR2', bound='MyForwardClass')
T_FR3 = TypeVar('T_FR3', bound=List['MyForwardClass'])
T_FR4 = TypeVar('T_FR4', 'MyForwardClass', 'MyAnotherForwardClass')


class MyForwardClass:
    pass


class MyAnotherForwardClass:
    pass


if HAS_PARAM_SPEC:
    P_FR1 = typing.ParamSpec('P_FR1', bound='int')  # type: ignore[misc]
    P_FR2 = typing.ParamSpec('P_FR2', bound='MyForwardClass')  # type: ignore[misc]
    P_FR3 = typing.ParamSpec('P_FR3', bound=List['MyForwardClass'])  # type: ignore[misc]


def test_forward_ref_at_type_var_limit():
    assert_norm_tv(
        T_FR1,
        NormTV(
            T_FR1,
            limit=Bound(nt_zero(int, source=ForwardRef('int'))),
            source=T_FR1
        ),
    )
    assert_norm_tv(
        T_FR2,
        NormTV(
            T_FR2,
            limit=Bound(nt_zero(MyForwardClass, source=ForwardRef('MyForwardClass'))),
            source=T_FR2,
        ),
    )
    assert_norm_tv(
        T_FR3,
        NormTV(
            T_FR3,
            limit=Bound(
                make_norm_type(
                    list,
                    (nt_zero(MyForwardClass, source=ForwardRef('MyForwardClass')), ),
                    source=List[ForwardRef('MyForwardClass')],
                )
            ),
            source=T_FR3,
        ),
    )
    assert_norm_tv(
        T_FR4,
        NormTV(
            T_FR4,
            limit=Constraints(
                (
                    make_norm_type(MyForwardClass, (), source=ForwardRef('MyForwardClass')),
                    make_norm_type(MyAnotherForwardClass, (), source=ForwardRef('MyAnotherForwardClass')),
                )
            ),
            source=T_FR4,
        ),
    )

    if HAS_PARAM_SPEC:
        assert_norm_tv(
            P_FR1,
            NormTV(
                P_FR1,
                limit=Bound(nt_zero(int, source=ForwardRef('int'))),
                source=P_FR1,
            ),
        )
        assert_norm_tv(
            P_FR2,
            NormTV(
                P_FR2,
                limit=Bound(nt_zero(MyForwardClass, source=ForwardRef('MyForwardClass'))),
                source=P_FR2,
            ),
        )
        assert_norm_tv(
            P_FR3,
            NormTV(
                P_FR3,
                limit=Bound(
                    make_norm_type(
                        list,
                        (nt_zero(MyForwardClass, source=ForwardRef('MyForwardClass')),),
                        source=List[ForwardRef('MyForwardClass')],
                    )
                ),
                source=P_FR3,
            ),
        )


@requires(HAS_PARAM_SPEC)
def test_param_spec_args_and_kwargs():
    from typing import ParamSpec, ParamSpecArgs, ParamSpecKwargs

    p1 = ParamSpec('p1')

    assert_strict_equal(
        normalize_type(p1.args),
        _NormParamSpecArgs(NormTV(p1, limit=Bound(nt_zero(Any)), source=p1), source=p1.args),
    )

    assert normalize_type(p1.args).origin == ParamSpecArgs

    assert_strict_equal(
        normalize_type(p1.kwargs),
        _NormParamSpecKwargs(NormTV(p1, limit=Bound(nt_zero(Any)), source=p1), source=p1.kwargs),
    )

    assert normalize_type(p1.kwargs).origin == ParamSpecKwargs


def test_bad_arg_types():
    with pytest.raises(ValueError):
        normalize_type(100)

    with pytest.raises(ValueError):
        normalize_type('string')

    with pytest.raises(ValueError):
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


@requires(HAS_STD_CLASSES_GENERICS)
def test_types_generic_alias():
    from types import GenericAlias

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
