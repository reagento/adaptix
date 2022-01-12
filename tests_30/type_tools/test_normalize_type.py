import collections
import re
import typing
from collections import abc as c_abc
from collections import defaultdict
from dataclasses import InitVar
from typing import (
    Any, Union, List, Optional,
    Tuple, Callable, NoReturn,
    Type, ClassVar, TypeVar,
    Dict, NewType, Set,
    FrozenSet, DefaultDict, Generic,
    Match, Pattern, cast
)

import pytest

from dataclass_factory_30.common import TypeHint
from dataclass_factory_30.feature_requirement import has_literal, has_final, has_annotated
from dataclass_factory_30.type_tools import NormType, normalize_type
from dataclass_factory_30.type_tools.normalize_type import (
    NormTV,
    BaseNormType,
    _create_norm_literal,
    Bound,
    Constraints
)


def nt_zero(origin):
    return NormType(origin, (), source=origin)


def assert_strict_equal(left: BaseNormType, right: BaseNormType):
    assert left.origin == right.origin
    assert left.args == right.args

    for l_arg, r_arg in zip(left.args, right.args):

        if isinstance(l_arg, BaseNormType) and isinstance(r_arg, BaseNormType):
            assert_strict_equal(l_arg, r_arg)

    if isinstance(left, NormTV) and isinstance(right, NormTV):
        assert left.variance == right.variance
        assert left.limit == right.limit

        if isinstance(left, Bound) and isinstance(right, Bound):
            assert_strict_equal(left.value, right.value)

        if isinstance(left, Constraints) and isinstance(right, Constraints):
            for l_constraints, r_constraints in zip(left.value, right.value):
                assert_strict_equal(l_constraints, r_constraints)

    assert left.source == right.source


def assert_normalize(tp: TypeHint, origin: TypeHint, args: List[typing.Hashable]):
    assert_strict_equal(
        normalize_type(tp),
        NormType(origin, tuple(args), source=tp)
    )


def test_atomic():
    assert_strict_equal(normalize_type(Any), nt_zero(Any))

    assert_strict_equal(normalize_type(int), nt_zero(int))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(str), nt_zero(str))
    assert_strict_equal(normalize_type(None), nt_zero(None))
    assert_strict_equal(
        normalize_type(type(None)),
        NormType(None, (), source=type(None))
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
    assert_normalize(
        tuple[int],
        tuple, [nt_zero(int)]
    )
    assert_normalize(
        Tuple[int],
        tuple, [nt_zero(int)]
    )
    assert_normalize(
        tuple[int, ...],
        tuple, [nt_zero(int), ...]
    )
    assert_normalize(
        Tuple[int, ...],
        tuple, [nt_zero(int), ...]
    )

    assert_normalize(tuple[()], tuple, [])
    assert_normalize(Tuple[()], tuple, [])

    any_str_placeholder = NormType(
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


def test_type():
    assert_normalize(type, type, [nt_zero(Any)])
    assert_normalize(Type, type, [nt_zero(Any)])

    assert_normalize(Type[int], type, [nt_zero(int)])

    assert_normalize(Type[Any], type, [nt_zero(Any)])

    assert_normalize(
        Type[Union[int, str]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str])]
    )

    assert_normalize(
        Union[Type[Union[int, str]], Type[bool]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str]), normalize_type(Type[bool])]
    )

    assert_normalize(
        Union[Type[Union[int, str]], Type[int]],
        Union, [normalize_type(Type[int]), normalize_type(Type[str])]
    )


@pytest.mark.parametrize(
    'tp',
    [ClassVar, InitVar],
)
def test_var_tag(tp):
    with pytest.raises(ValueError):
        normalize_type(tp)

    assert_normalize(
        tp[int],
        tp, [nt_zero(int)]
    )


def n_lit(*args):
    return _create_norm_literal(args)


@has_literal
def test_literal():
    from typing import Literal

    with pytest.raises(ValueError):
        normalize_type(Literal)

    assert_normalize(Literal['a'], Literal, ['a'])
    assert_normalize(Literal['a', 'b'], Literal, ['a', 'b'])
    assert_normalize(Literal[None], None, [])

    assert_normalize(Optional[Literal[None]], None, [])

    assert_normalize(
        Union[Literal['a'], Literal['b']],
        Literal, ['a', 'b']
    )

    assert_normalize(
        Union[Literal['a'], Literal['b'], int],
        Union, [
            n_lit('a', 'b'),
            nt_zero(int)
        ]
    )

    assert_normalize(
        Union[Literal['a'], int, Literal['b']],
        Union, [
            n_lit('a'),
            nt_zero(int),
            n_lit('b'),
        ]
    )

    assert_normalize(
        Union[int, Literal['a'], Literal['b']],
        Union, [
            nt_zero(int),
            n_lit('a', 'b'),
        ]
    )


@has_final
def test_final():
    from typing import Final

    with pytest.raises(ValueError):
        assert normalize_type(Final)

    assert_normalize(
        Final[int],
        Final, [nt_zero(int)]
    )


@has_annotated
def test_annotated():
    from typing import Annotated

    with pytest.raises(ValueError):
        normalize_type(Annotated)

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


def test_union():
    with pytest.raises(ValueError):
        normalize_type(Union)

    assert_normalize(
        Union[int, str],
        Union, [normalize_type(int), normalize_type(str)]
    )

    assert_normalize(
        Union[list, List, int],
        Union, [normalize_type(Union[list, List]), normalize_type(int)]
    )
    assert_normalize(
        Union[list, List],
        list, [nt_zero(Any)]
    )
    assert_normalize(
        Union[list, str, List],
        Union, [normalize_type(Union[list, List]), normalize_type(str)]
    )

    assert_normalize(
        Union[Type[list], Type[Union[List, str]]],
        Union, [
            normalize_type(Union[Type[list], Type[List]]),
            normalize_type(Type[str])
        ]
    )

    # Union[int] == int   # normalization does not need


def test_optional():
    with pytest.raises(ValueError):
        normalize_type(Optional)

    assert_normalize(
        Optional[int],
        Union, [nt_zero(int), NormType(None, (), source=type(None))]
    )

    assert_normalize(
        Optional[None],
        None, []
    )


def test_new_type():
    with pytest.raises(ValueError):
        normalize_type(NewType)

    new_int = NewType('new_int', int)
    assert normalize_type(new_int) == nt_zero(new_int)


def assert_norm_tv(tv: TypeVar, target: NormTV):
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
def test_type_var(variance: dict):
    t1 = TypeVar("t1", **variance)

    assert_norm_tv(
        t1,
        NormTV(t1, limit=Bound(nt_zero(Any)))
    )

    t2 = TypeVar("t2", bound=int, **variance)

    assert_norm_tv(
        t2,
        NormTV(t2, limit=Bound(nt_zero(int)))
    )

    t3 = TypeVar("t3", int, str, **variance)

    assert_norm_tv(
        t3,
        NormTV(t3, limit=Constraints((nt_zero(int), nt_zero(str))))
    )

    t4 = TypeVar("t4", list, str, List, **variance)

    t4_union = cast(NormType, normalize_type(Union[list, List]))

    assert_norm_tv(
        t4,
        NormTV(
            t4, limit=Constraints(
                (t4_union, nt_zero(str))
            )
        )
    )


K = TypeVar('K')
V = TypeVar('V')
H = TypeVar('H', int, str)


class MyGeneric1(Generic[K]):
    pass


class MyGeneric2(Generic[K, V]):
    pass


class MyGeneric3(MyGeneric1[K], Generic[K, V, H]):
    pass


T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')


def any_tv(tv: TypeVar):
    return NormTV(tv, Bound(nt_zero(Any)))


def test_generic():
    assert_normalize(MyGeneric1, MyGeneric1, [nt_zero(Any)])
    assert_normalize(MyGeneric1[int], MyGeneric1, [nt_zero(int)])
    assert_normalize(MyGeneric1[T1], MyGeneric1, [any_tv(T1)])

    assert_normalize(MyGeneric2, MyGeneric2, [nt_zero(Any), nt_zero(Any)])
    assert_normalize(MyGeneric2[int, str], MyGeneric2, [nt_zero(int), nt_zero(str)])
    assert_normalize(MyGeneric2[T1, T2], MyGeneric2, [any_tv(T1), any_tv(T2)])
    assert_normalize(MyGeneric2[T1, T1], MyGeneric2, [any_tv(T1), any_tv(T1)])

    h_implicit = normalize_type(Union[int, str])

    assert_normalize(MyGeneric3, MyGeneric3, [nt_zero(Any), nt_zero(Any), h_implicit])
    assert_normalize(MyGeneric3[int, str, bool], MyGeneric3, [nt_zero(int), nt_zero(str), nt_zero(bool)])
    assert_normalize(MyGeneric3[T1, T2, T3], MyGeneric3, [any_tv(T1), any_tv(T2), any_tv(T3)])
    assert_normalize(MyGeneric3[T1, T1, T1], MyGeneric3, [any_tv(T1), any_tv(T1), any_tv(T1)])


def test_bad_arg_types():
    with pytest.raises(ValueError):
        normalize_type(100)

    with pytest.raises(ValueError):
        normalize_type('string')

    with pytest.raises(ValueError):
        normalize_type(TypeVar)
