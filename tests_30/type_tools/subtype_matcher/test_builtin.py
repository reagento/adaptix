import sys
from typing import (
    Any, Callable, NoReturn,
    List, Type, Set, FrozenSet,
    Tuple, DefaultDict, Annotated,
    Dict, ChainMap, NewType, Counter,
    OrderedDict, Union, Final, ClassVar,
)
from typing import (
    Protocol, TypedDict,
    runtime_checkable,
)

import pytest

from .conftest import matcher, assert_subtype_shift, Class, SubClass


@pytest.mark.parametrize(
    'tp',
    [int, str, bytes, None, Class, SubClass]
)
def test_any(tp):
    assert_subtype_shift(tp, Any)


def test_atomic():
    assert matcher.is_subtype(Any, Any)
    assert matcher.is_subtype(None, None)
    assert matcher.is_subtype(NoReturn, NoReturn)

    assert_subtype_shift(
        bool,
        int,
    )
    assert_subtype_shift(
        SubClass,
        Class,
    )


@pytest.mark.parametrize(
    'tp',
    [Final, ClassVar]
)
def test_tags(tp):
    assert matcher.is_subtype(
        tp[int],
        int,
    )
    assert matcher.is_subtype(
        int,
        tp[int],
    )
    assert matcher.is_subtype(
        tp[int],
        tp[int],
    )


@pytest.mark.parametrize(
    'tp',
    [
        List, Type, FrozenSet,
        Counter, Counter, Set,
    ]
)
def test_builtin_generic_one_arg(tp):
    assert matcher.is_subtype(tp, tp)
    assert matcher.is_subtype(tp[int], tp[int])

    assert_subtype_shift(
        tp[bool],
        tp[int],
    )

    assert matcher.is_subtype(tp[Class], tp[Class])
    assert matcher.is_subtype(tp[SubClass], tp[SubClass])

    assert_subtype_shift(
        tp[SubClass],
        tp[Class],
    )


@pytest.mark.parametrize(
    'tp',
    [
        Dict, DefaultDict, FrozenSet,
        OrderedDict, ChainMap, Set,
    ]
)
def test_builtin_generic_two_args(tp):
    assert matcher.is_subtype(tp, tp)
    assert matcher.is_subtype(tp[int, int], tp[int, int])

    assert_subtype_shift(
        tp[bool, bool],
        tp[int, int],
    )

    assert not matcher.is_subtype(
        tp[bool, int],
        tp[int, bool],
    )
    assert not matcher.is_subtype(
        tp[int, bool],
        tp[bool, int],
    )


@pytest.mark.skipif(sys.version_info < (3, 8), reason='Need Python >= 3.8')
def test_literal():
    from typing import Literal

    assert matcher.is_subtype(
        Literal['a'],
        Literal['a'],
    )

    assert not matcher.is_subtype(
        Literal['a'],
        Literal['b'],
    )
    assert not matcher.is_subtype(
        Literal['b'],
        Literal['a'],
    )

    assert_subtype_shift(
        Literal['a'],
        Literal['a', 'b'],
    )

    assert not matcher.is_subtype(
        Literal['b', 'c'],
        Literal['a', 'b'],
    )
    assert not matcher.is_subtype(
        Literal['a', 'b'],
        Literal['b', 'c'],
    )


def test_union():
    assert matcher.is_subtype(
        Union[int, str],
        Union[int, str],
    )
    assert matcher.is_subtype(
        Union[int, str],
        Union[str, int],
    )
    assert matcher.is_subtype(
        Union[str, int],
        Union[int, str],
    )

    assert_subtype_shift(
        Union[str, int],
        Union[str, int, bytes],
    )

    assert_subtype_shift(
        Union[bool, str],
        Union[int, str],
    )


def test_callable():
    assert matcher.is_subtype(Callable, Callable)

    assert_subtype_shift(
        Callable[..., SubClass],
        Callable[..., Class],
    )
    assert_subtype_shift(
        Callable[[], SubClass],
        Callable[..., Class],
    )

    assert_subtype_shift(
        Callable[[Class], SubClass],
        Callable[..., Class],
    )
    assert_subtype_shift(
        Callable[[SubClass], SubClass],
        Callable[..., Class]
    )
    assert_subtype_shift(
        Callable[[Class, Class], SubClass],
        Callable[..., Class]
    )

    assert_subtype_shift(
        Callable[[Class, Class], SubClass],
        Callable[[SubClass, SubClass], Class],
    )

    assert not matcher.is_subtype(
        Callable[[int, int], int],
        Callable[[int, int, int], int],
    )
    assert not matcher.is_subtype(
        Callable[[int, int, int], int],
        Callable[[int, int], int],
    )

    assert matcher.is_subtype(
        Callable[[], NoReturn],
        Callable[[], Any],
    )


def test_tuple():
    assert matcher.is_subtype(Tuple, Tuple)

    assert_subtype_shift(
        Tuple[bool],
        Tuple[int],
    )

    assert not matcher.is_subtype(
        Tuple[int],
        Tuple[int, int],
    )
    assert not matcher.is_subtype(
        Tuple[int, int],
        Tuple[int],
    )

    assert_subtype_shift(
        Tuple[bool, int],
        Tuple[int, int],
    )
    assert_subtype_shift(
        Tuple[int, bool],
        Tuple[int, int],
    )
    assert_subtype_shift(
        Tuple[bool, bool],
        Tuple[int, int],
    )

    assert_subtype_shift(
        Tuple[int],
        Tuple[int, ...],
    )
    assert_subtype_shift(
        Tuple[int, int],
        Tuple[int, ...],
    )


NewStr = NewType('NewStr', str)


def test_new_type():
    assert not matcher.is_subtype(
        str,
        NewStr,
    )

    assert not matcher.is_subtype(
        NewStr,
        str,
    )

    assert matcher.is_subtype(
        NewStr,
        NewStr,
    )


def test_annotated():
    assert matcher.is_subtype(
        int,
        Annotated[int, 'meta'],
    )

    assert matcher.is_subtype(
        Annotated[int, 'meta'],
        int,
    )

    assert matcher.is_subtype(
        bool,
        Annotated[int, 'meta'],
    )

    assert matcher.is_subtype(
        Annotated[bool, 'meta'],
        int,
    )


class Proto(Protocol):
    def foo(self) -> bool:
        pass


@runtime_checkable
class RtProto(Protocol):
    def foo(self) -> bool:
        pass


class ImplProto:
    def foo(self) -> bool:
        pass


class BadImplProto:
    def foo(self) -> str:
        pass


def test_protocol():
    assert_subtype_shift(
        ImplProto,
        Proto,
    )
    assert_subtype_shift(
        BadImplProto,
        Proto,
    )

    assert_subtype_shift(
        ImplProto,
        RtProto,
    )
    assert_subtype_shift(
        BadImplProto,
        RtProto,
    )


class TDBig(TypedDict):
    a: int
    b: str


class TDSmall(TypedDict):
    a: int


class TDBigUT(TypedDict, total=False):
    a: int
    b: str


class TDSmallUT(TypedDict, total=False):
    a: int


def test_typed_dict():
    assert_subtype_shift(
        TDBig,
        TDSmall,
    )

    assert_subtype_shift(
        TDBigUT,
        TDSmallUT,
    )

    # we repeat behavior of PyCharm and MyPy
    assert not matcher.is_subtype(TDBigUT, TDSmall)
    assert not matcher.is_subtype(TDSmall, TDBigUT)

    assert not matcher.is_subtype(TDBig, TDSmallUT)
    assert not matcher.is_subtype(TDSmallUT, TDBig)
