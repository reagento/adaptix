import collections
import re
import sys
import typing
from collections import defaultdict
from collections import abc as c_abc
from typing import (
    Any, Union, List, Optional,
    Tuple, Callable, NoReturn,
    Type, ClassVar, TypeVar,
    Dict, NewType, Set,
    FrozenSet, DefaultDict, Generic,
    Match, Pattern, AnyStr
)

import pytest

from dataclass_factory_30.type_checker import normalize_type

T = TypeVar('T')


def n(value: T) -> Tuple[T, Tuple[()]]:
    return value, ()


def test_atomic():
    assert normalize_type(Any) == (Any, ())

    assert normalize_type(int) == (int, ())
    assert normalize_type(str) == (str, ())
    assert normalize_type(None) == (None, ())
    assert normalize_type(type(None)) == (None, ())

    assert normalize_type(object) == (object, ())

    assert normalize_type(NoReturn) == (NoReturn, ())


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
    assert normalize_type(tp) == (tp, (n(Any),))
    assert normalize_type(alias) == (tp, (n(Any),))
    assert normalize_type(tp[int]) == (tp, (n(int),))
    assert normalize_type(alias[int]) == (tp, (n(int),))


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
    assert normalize_type(tp) == (tp, (n(Any), n(Any)))
    assert normalize_type(alias) == (tp, (n(Any), n(Any)))

    assert normalize_type(dict[int, str]) == (tp, (n(int), n(str)))
    assert normalize_type(alias[int, str]) == (tp, (n(int), n(str)))


def test_special_generics():
    assert normalize_type(tuple) == (tuple, (n(Any), ...))
    assert normalize_type(Tuple) == (tuple, (n(Any), ...))
    assert normalize_type(tuple[int]) == (tuple, (n(int),))
    assert normalize_type(Tuple[int]) == (tuple, (n(int),))
    assert normalize_type(tuple[int, ...]) == (tuple, (n(int), ...))
    assert normalize_type(Tuple[int, ...]) == (tuple, (n(int), ...))

    assert normalize_type(tuple[()]) == (tuple, ())
    assert normalize_type(Tuple[()]) == (tuple, ())

    assert normalize_type(Pattern) == (re.Pattern, (n(AnyStr),))
    assert normalize_type(Match) == (re.Match, (n(AnyStr),))
    assert normalize_type(Pattern[bytes]) == (re.Pattern, (n(bytes),))
    assert normalize_type(Match[bytes]) == (re.Match, (n(bytes),))


def test_callable():
    assert normalize_type(Callable) == (c_abc.Callable, ([...], n(Any)))
    assert normalize_type(Callable[..., Any]) == (c_abc.Callable, (..., n(Any)))
    assert normalize_type(Callable[..., int]) == (c_abc.Callable, (..., n(int)))
    assert normalize_type(Callable[[str], int]) == (c_abc.Callable, ([n(str)], n(int)))
    assert normalize_type(Callable[[str, bytes], int]) == (c_abc.Callable, ([n(str), n(bytes)], n(int)))

    assert normalize_type(Callable[..., NoReturn]) == (c_abc.Callable, (..., n(NoReturn)))


def test_type():
    assert normalize_type(type) == (type, (n(Any),))
    assert normalize_type(Type) == (type, (n(Any),))

    assert normalize_type(Type[int]) == (type, (n(int),))


def test_class_var():
    with pytest.raises(ValueError):
        normalize_type(ClassVar)

    assert normalize_type(ClassVar[int]) == (ClassVar, (n(int),))


@pytest.mark.skipif(sys.version_info < (3, 8), reason='Need Python >= 3.8')
def test_literal():
    from typing import Literal

    with pytest.raises(ValueError):
        normalize_type(Literal)

    assert normalize_type(Literal['a']) == (Literal, ('a',))
    assert normalize_type(Literal['a', 'b']) == (Literal, ('a', 'b'))
    assert normalize_type(Literal[None]) == (None, ())

    assert normalize_type(Optional[Literal[None]]) == (None, ())

    assert normalize_type(
        Union[Literal['a'], Literal['b']]
    ) == Literal['a', 'b']

    assert normalize_type(
        Union[Literal['a'], Literal['b'], int]
    ) == Union[Literal['a', 'b'], int]

    assert normalize_type(
        Union[Literal['a'], int, Literal['b']]
    ) == Union[Literal['a'], int, Literal['b']]

    assert normalize_type(
        Union[int, Literal['a'], Literal['b']]
    ) == Union[int, Literal['a', 'b']]


@pytest.mark.skipif(sys.version_info < (3, 8), reason='Need Python >= 3.8')
def test_final():
    from typing import Final

    with pytest.raises(ValueError):
        assert normalize_type(Final)

    assert normalize_type(Final[int]) == (Final, (n(int),))


@pytest.mark.skipif(sys.version_info < (3, 9), reason='Need Python >= 3.9')
def test_annotated():
    from typing import Annotated

    with pytest.raises(ValueError):
        normalize_type(Annotated)

    assert normalize_type(Annotated[int, 'metadata']) == (Annotated, (n(int), 'metadata'))
    assert normalize_type(Annotated[int, str]) == (Annotated, (n(int), str))
    assert normalize_type(Annotated[int, int]) == (Annotated, (n(int), int))


def test_union():
    with pytest.raises(ValueError):
        normalize_type(Union)

    assert normalize_type(Union[int, str]) == (Union, (n(int), n(str)))

    assert normalize_type(Union[list, List, int]) == (Union, (normalize_type(list), n(int)))
    assert normalize_type(Union[list, List]) == normalize_type(list)
    assert normalize_type(Union[list, str, List]) == (
        Union, (normalize_type(list), normalize_type(str))
    )

    # Union[int] == int   # normalization does not need


def test_optional():
    with pytest.raises(ValueError):
        normalize_type(Optional)

    assert normalize_type(Optional[int]) == (Union, (n(int), n(None)))

    assert normalize_type(Optional[None]) == (None, ())


def test_new_type():
    with pytest.raises(ValueError):
        normalize_type(NewType)

    new_int = NewType('new_int', int)
    assert normalize_type(new_int) == (new_int, ())


class MyGeneric(Generic[T]):
    pass


class Child(MyGeneric[int]):
    pass


class GenericChild(MyGeneric):
    pass


def test_generic():
    assert normalize_type(MyGeneric) == (MyGeneric, (n(T),))
    assert normalize_type(MyGeneric[T]) == (MyGeneric, (n(T),))
    assert normalize_type(MyGeneric[int]) == (MyGeneric, (n(int),))

    assert normalize_type(Child) == (Child, ())

    assert normalize_type(GenericChild) == (GenericChild, ())
    assert normalize_type(GenericChild[int]) == (GenericChild, ())


def test_bad_arg_types():
    with pytest.raises(ValueError):
        normalize_type(100)

    with pytest.raises(ValueError):
        normalize_type('string')
