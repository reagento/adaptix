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

from .conftest import is_subtype, assert_swapped_is_subtype, Class, SubClass, id_gen


@pytest.mark.parametrize(
    'tp',
    [int, str, bytes, None, Class, SubClass],
    ids=id_gen,
)
def test_any(tp):
    assert_swapped_is_subtype(tp, Any)


def test_atomic():
    assert is_subtype(Any, Any)
    assert is_subtype(None, None)
    assert is_subtype(NoReturn, NoReturn)

    assert_swapped_is_subtype(
        bool,
        int,
    )
    assert_swapped_is_subtype(
        SubClass,
        Class,
    )


@pytest.mark.parametrize(
    'tp',
    [Final, ClassVar],
    ids=id_gen,
)
def test_tags(tp):
    assert is_subtype(
        tp[int],
        int,
    )
    assert is_subtype(
        int,
        tp[int],
    )
    assert is_subtype(
        tp[int],
        tp[int],
    )


@pytest.mark.parametrize(
    'tp',
    [
        List, Type, FrozenSet,
        Counter, Counter, Set,
    ],
    ids=id_gen,
)
def test_builtin_generic_one_arg(tp):
    assert is_subtype(tp, tp)
    assert is_subtype(tp[int], tp[int])

    assert_swapped_is_subtype(
        tp[bool],
        tp[int],
    )

    assert is_subtype(tp[Class], tp[Class])
    assert is_subtype(tp[SubClass], tp[SubClass])

    assert_swapped_is_subtype(
        tp[SubClass],
        tp[Class],
    )


@pytest.mark.parametrize(
    'tp',
    [
        Dict, DefaultDict, FrozenSet,
        OrderedDict, ChainMap, Set,
    ],
    ids=id_gen,
)
def test_builtin_generic_two_args(tp):
    assert is_subtype(tp, tp)
    assert is_subtype(tp[int, int], tp[int, int])

    assert_swapped_is_subtype(
        tp[bool, bool],
        tp[int, int],
    )

    assert not is_subtype(
        tp[bool, int],
        tp[int, bool],
    )
    assert not is_subtype(
        tp[int, bool],
        tp[bool, int],
    )


@pytest.mark.skipif(sys.version_info < (3, 8), reason='Need Python >= 3.8')
def test_literal():
    from typing import Literal

    assert is_subtype(
        Literal['a'],
        Literal['a'],
    )

    assert not is_subtype(
        Literal['a'],
        Literal['b'],
    )
    assert not is_subtype(
        Literal['b'],
        Literal['a'],
    )

    assert_swapped_is_subtype(
        Literal['a'],
        Literal['a', 'b'],
    )

    assert not is_subtype(
        Literal['b', 'c'],
        Literal['a', 'b'],
    )
    assert not is_subtype(
        Literal['a', 'b'],
        Literal['b', 'c'],
    )


def test_union():
    assert is_subtype(
        Union[int, str],
        Union[int, str],
    )
    assert is_subtype(
        Union[int, str],
        Union[str, int],
    )
    assert is_subtype(
        Union[str, int],
        Union[int, str],
    )

    assert_swapped_is_subtype(
        Union[str, int],
        Union[str, int, bytes],
    )

    assert_swapped_is_subtype(
        Union[bool, str],
        Union[int, str],
    )


def test_callable():
    assert is_subtype(Callable, Callable)

    assert_swapped_is_subtype(
        Callable[..., SubClass],
        Callable[..., Class],
    )
    assert_swapped_is_subtype(
        Callable[[], SubClass],
        Callable[..., Class],
    )

    assert_swapped_is_subtype(
        Callable[[Class], SubClass],
        Callable[..., Class],
    )
    assert_swapped_is_subtype(
        Callable[[SubClass], SubClass],
        Callable[..., Class]
    )
    assert_swapped_is_subtype(
        Callable[[Class, Class], SubClass],
        Callable[..., Class]
    )

    assert_swapped_is_subtype(
        Callable[[Class, Class], SubClass],
        Callable[[SubClass, SubClass], Class],
    )

    assert not is_subtype(
        Callable[[int, int], int],
        Callable[[int, int, int], int],
    )
    assert not is_subtype(
        Callable[[int, int, int], int],
        Callable[[int, int], int],
    )

    assert is_subtype(
        Callable[[], NoReturn],
        Callable[[], Any],
    )


def test_tuple():
    assert is_subtype(Tuple, Tuple)

    assert_swapped_is_subtype(
        Tuple[bool],
        Tuple[int],
    )

    assert not is_subtype(
        Tuple[int],
        Tuple[int, int],
    )
    assert not is_subtype(
        Tuple[int, int],
        Tuple[int],
    )

    assert_swapped_is_subtype(
        Tuple[bool, int],
        Tuple[int, int],
    )
    assert_swapped_is_subtype(
        Tuple[int, bool],
        Tuple[int, int],
    )
    assert_swapped_is_subtype(
        Tuple[bool, bool],
        Tuple[int, int],
    )

    assert_swapped_is_subtype(
        Tuple[int],
        Tuple[int, ...],
    )
    assert_swapped_is_subtype(
        Tuple[int, int],
        Tuple[int, ...],
    )


NewStr = NewType('NewStr', str)


def test_new_type():
    assert not is_subtype(
        str,
        NewStr,
    )

    assert not is_subtype(
        NewStr,
        str,
    )

    assert is_subtype(
        NewStr,
        NewStr,
    )


def test_annotated():
    assert is_subtype(
        int,
        Annotated[int, 'meta'],
    )

    assert is_subtype(
        Annotated[int, 'meta'],
        int,
    )

    assert is_subtype(
        bool,
        Annotated[int, 'meta'],
    )

    assert is_subtype(
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
    assert_swapped_is_subtype(
        ImplProto,
        Proto,
    )
    assert_swapped_is_subtype(
        BadImplProto,
        Proto,
    )

    assert_swapped_is_subtype(
        ImplProto,
        RtProto,
    )
    assert_swapped_is_subtype(
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
    assert_swapped_is_subtype(
        TDBig,
        TDSmall,
    )

    assert_swapped_is_subtype(
        TDBigUT,
        TDSmallUT,
    )

    # we repeat behavior of PyCharm and MyPy
    assert not is_subtype(TDBigUT, TDSmall)
    assert not is_subtype(TDSmall, TDBigUT)

    assert not is_subtype(TDBig, TDSmallUT)
    assert not is_subtype(TDSmallUT, TDBig)
