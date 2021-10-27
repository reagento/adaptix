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
    Match, Pattern, AnyStr
)

import pytest

from dataclass_factory_30.type_tools import NormType, normalize_type
from dataclass_factory_30.type_tools.normalize_type import NormTV, T_co
from dataclass_factory_30.feature_requirement import has_literal, has_final, has_annotated

T = TypeVar('T')


def test_atomic():
    assert normalize_type(Any) == NormType(Any)

    assert normalize_type(int) == NormType(int)
    assert normalize_type(str) == NormType(str)
    assert normalize_type(None) == NormType(None)
    assert normalize_type(type(None)) == NormType(None)

    assert normalize_type(object) == NormType(object)

    assert normalize_type(NoReturn) == NormType(NoReturn)


@pytest.mark.parametrize(
    ['tp', 'alias'],
    [
        (list, List),
        (set, Set),
        (frozenset, FrozenSet),
        (collections.Counter, typing.Counter),
        (collections.deque, typing.Deque),
    ]
)
def test_generic_concrete_one_arg(tp, alias):
    assert normalize_type(tp) == NormType(tp, [NormTV(T_co, is_template=True)])
    assert normalize_type(alias) == NormType(tp, [NormTV(T_co, is_template=True)])
    assert normalize_type(tp[int]) == NormType(tp, [NormType(int)])
    assert normalize_type(alias[int]) == NormType(tp, [NormType(int)])


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
    assert normalize_type(tp) == NormType(
        tp, [NormTV(T_co, is_template=True), NormTV(T_co, is_template=True)]
    )
    assert normalize_type(alias) == NormType(
        tp, [NormTV(T_co, is_template=True), NormTV(T_co, is_template=True)]
    )

    assert normalize_type(tp[int, str]) == NormType(tp, [NormType(int), NormType(str)])
    assert normalize_type(alias[int, str]) == NormType(tp, [NormType(int), NormType(str)])


def test_special_generics():
    assert normalize_type(tuple) == NormType(tuple, [NormTV(T_co, is_template=True), ...])
    assert normalize_type(Tuple) == NormType(tuple, [NormTV(T_co, is_template=True), ...])
    assert normalize_type(tuple[int]) == NormType(tuple, [NormType(int)])
    assert normalize_type(Tuple[int]) == NormType(tuple, [NormType(int)])
    assert normalize_type(tuple[int, ...]) == NormType(tuple, [NormType(int), ...])
    assert normalize_type(Tuple[int, ...]) == NormType(tuple, [NormType(int), ...])

    assert normalize_type(tuple[()]) == NormType(tuple, [])
    assert normalize_type(Tuple[()]) == NormType(tuple, [])

    assert normalize_type(Pattern) == NormType(re.Pattern, [NormTV(AnyStr, is_template=True)])
    assert normalize_type(Match) == NormType(re.Match, [NormTV(AnyStr, is_template=True)])
    assert normalize_type(Pattern[bytes]) == NormType(re.Pattern, [NormType(bytes)])
    assert normalize_type(Match[bytes]) == NormType(re.Match, [NormType(bytes)])


def test_callable():
    assert normalize_type(Callable) == NormType(
        c_abc.Callable, [..., NormTV(T_co, is_template=True)]
    )
    assert normalize_type(Callable[..., Any]) == NormType(
        c_abc.Callable, [..., NormType(Any)]
    )
    assert normalize_type(Callable[..., int]) == NormType(
        c_abc.Callable, [..., NormType(int)]
    )
    assert normalize_type(Callable[[str], int]) == NormType(
        c_abc.Callable, [[NormType(str)], NormType(int)]
    )
    assert normalize_type(Callable[[str, bytes], int]) == NormType(
        c_abc.Callable, [[NormType(str), NormType(bytes)], NormType(int)]
    )

    assert normalize_type(Callable[..., NoReturn]) == NormType(
        c_abc.Callable, [..., NormType(NoReturn)]
    )


def test_type():
    assert normalize_type(type) == NormType(type, [NormTV(T_co, is_template=True)])
    assert normalize_type(Type) == NormType(type, [NormTV(T_co, is_template=True)])

    assert normalize_type(Type[int]) == NormType(type, [NormType(int)])

    assert normalize_type(Type[Any]) == NormType(type, [NormType(Any)])


@pytest.mark.parametrize(
    'tp',
    [ClassVar, InitVar]
)
def test_var_tag(tp):
    with pytest.raises(ValueError):
        normalize_type(tp)

    assert normalize_type(tp[int]) == NormType(tp, [NormType(int)])


@has_literal
def test_literal():
    from typing import Literal

    with pytest.raises(ValueError):
        normalize_type(Literal)

    assert normalize_type(Literal['a']) == NormType(Literal, ['a'])
    assert normalize_type(Literal['a', 'b']) == NormType(Literal, ['a', 'b'])
    assert normalize_type(Literal[None]) == NormType(None)

    assert normalize_type(Optional[Literal[None]]) == NormType(None)

    assert normalize_type(
        Union[Literal['a'], Literal['b']]
    ) == NormType(Literal, ['a', 'b'])

    assert normalize_type(
        Union[Literal['a'], Literal['b'], int]
    ) == NormType(
        Union, [NormType(Literal, ['a', 'b']), NormType(int)]
    )

    assert normalize_type(
        Union[Literal['a'], int, Literal['b']]
    ) == NormType(
        Union, [
            NormType(Literal, ['a']), NormType(int), NormType(Literal, ['b'])
        ]
    )

    assert normalize_type(
        Union[int, Literal['a'], Literal['b']]
    ) == NormType(
        Union, [NormType(int), NormType(Literal, ['a', 'b'])]
    )


@has_final
def test_final():
    from typing import Final

    with pytest.raises(ValueError):
        assert normalize_type(Final)

    assert normalize_type(Final[int]) == NormType(Final, [NormType(int)])


@has_annotated
def test_annotated():
    from typing import Annotated

    with pytest.raises(ValueError):
        normalize_type(Annotated)

    assert normalize_type(Annotated[int, 'metadata']) == NormType(
        Annotated, [NormType(int), 'metadata']
    )
    assert normalize_type(Annotated[int, str]) == NormType(
        Annotated, [NormType(int), str]
    )
    assert normalize_type(Annotated[int, int]) == NormType(
        Annotated, [NormType(int), int]
    )


def test_union():
    with pytest.raises(ValueError):
        normalize_type(Union)

    assert normalize_type(Union[int, str]) == NormType(
        Union, [NormType(int), NormType(str)]
    )

    assert normalize_type(Union[list, List, int]) == NormType(
        Union, [normalize_type(list), NormType(int)]
    )
    assert normalize_type(Union[list, List]) == normalize_type(list)
    assert normalize_type(Union[list, str, List]) == NormType(
        Union, [normalize_type(list), normalize_type(str)]
    )

    # Union[int] == int   # normalization does not need


def test_optional():
    with pytest.raises(ValueError):
        normalize_type(Optional)

    assert normalize_type(Optional[int]) == NormType(
        Union, [NormType(int), NormType(None)]
    )

    assert normalize_type(Optional[None]) == NormType(None)


def test_new_type():
    with pytest.raises(ValueError):
        normalize_type(NewType)

    new_int = NewType('new_int', int)
    assert normalize_type(new_int) == NormType(new_int)


K = TypeVar('K')
V = TypeVar('V')


class MyGeneric(Generic[T]):
    pass


class GChild(MyGeneric):
    pass


class GConChild(MyGeneric[int]):
    pass


class SubGenChild1(MyGeneric, Generic[K]):
    pass


class SubGenChild2(MyGeneric, Generic[T, K]):
    pass


class SubGenChild3(MyGeneric, Generic[K, T]):
    pass


class SubGenChild4(MyGeneric, Generic[K, V]):
    pass


def test_generic():
    assert normalize_type(MyGeneric) == NormType(MyGeneric, [NormTV(T, is_template=True)])
    assert normalize_type(MyGeneric[T]) == NormType(MyGeneric, [NormTV(T)])
    assert normalize_type(MyGeneric[int]) == NormType(MyGeneric, [NormType(int)])

    assert normalize_type(GConChild) == NormType(GConChild)
    assert normalize_type(GChild) == NormType(GChild)

    assert normalize_type(SubGenChild1) == NormType(SubGenChild1, [NormTV(K, is_template=True)])
    assert normalize_type(SubGenChild1[int]) == NormType(SubGenChild1, [NormType(int)])

    assert normalize_type(SubGenChild2) == NormType(
        SubGenChild2, [NormTV(T, is_template=True), NormTV(K, is_template=True)]
    )
    assert normalize_type(SubGenChild2[int, str]) == NormType(
        SubGenChild2, [NormType(int), NormType(str)]
    )

    assert normalize_type(SubGenChild3) == NormType(
        SubGenChild3, [NormTV(K, is_template=True), NormTV(T, is_template=True)]
    )
    assert normalize_type(SubGenChild3[int, str]) == NormType(
        SubGenChild3, [NormType(int), NormType(str)]
    )

    assert normalize_type(SubGenChild4) == NormType(
        SubGenChild4, [NormTV(K, is_template=True), NormTV(V, is_template=True)]
    )
    assert normalize_type(SubGenChild4[int, str]) == NormType(
        SubGenChild4, [NormType(int), NormType(str)]
    )


def test_bad_arg_types():
    with pytest.raises(ValueError):
        normalize_type(100)

    with pytest.raises(ValueError):
        normalize_type('string')
