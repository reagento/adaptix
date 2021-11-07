from typing import (
    Any, Callable, NoReturn,
    List, Type, Set, FrozenSet,
    Tuple, DefaultDict,
    Dict, ChainMap, NewType, Counter,
    OrderedDict, Union, ClassVar,
)
from typing import (
    runtime_checkable,
)

import pytest

from dataclass_factory_30.feature_requirement import (
    has_literal, has_final, has_typed_dict,
    has_protocol, has_annotated
)
from .conftest import (
    is_subtype, assert_swapped_is_subtype,
    Class, SubClass
)


@pytest.mark.parametrize(
    'tp',
    [int, str, bytes, None, Class, SubClass],
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


def test_class_var():
    assert is_subtype(
        ClassVar[int],
        int,
    )
    assert is_subtype(
        int,
        ClassVar[int],
    )
    assert is_subtype(
        ClassVar[int],
        ClassVar[int],
    )


@has_final
def test_final():
    from typing import Final

    assert is_subtype(
        Final[int],
        int,
    )
    assert is_subtype(
        int,
        Final[int],
    )
    assert is_subtype(
        Final[int],
        Final[int],
    )


@pytest.mark.parametrize(
    'tp',
    [
        List, Type, Counter,
        FrozenSet, Set,
    ],
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
        Dict, DefaultDict,
        OrderedDict, ChainMap,
    ],
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


@has_literal
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
    assert_swapped_is_subtype(
        int,
        Union[int, str],
    )
    assert_swapped_is_subtype(
        bool,
        Union[int, str],
    )
    assert_swapped_is_subtype(
        str,
        Union[int, str],
    )

    assert is_subtype(
        Union[int, bool],
        int,
    )
    assert is_subtype(
        int,
        Union[int, bool],
    )

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


@has_annotated
def test_annotated():
    from typing import Annotated

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


@has_protocol
def test_protocol():
    from typing import Protocol

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

    class InheritedImplProto(Proto):
        def foo(self) -> bool:
            pass

    class InheritedBadImplProto(Proto):
        def foo(self) -> str:  # type: ignore
            pass

    class InheritedImplRtProto(RtProto):
        def foo(self) -> bool:
            pass

    class InheritedBadImplRtProto(RtProto):
        def foo(self) -> str:  # type: ignore
            pass

    class ProtoAttr:
        foo = '123'

    class OtherProto(Protocol):
        def foo(self) -> bool:
            pass

    @runtime_checkable
    class OtherRtProto(Protocol):
        def foo(self) -> bool:
            pass

    with pytest.raises(ValueError):
        is_subtype(ImplProto, Proto)

    assert_swapped_is_subtype(
        ImplProto,
        RtProto,
    )
    # we checks only methods name
    assert_swapped_is_subtype(
        BadImplProto,
        RtProto,
    )

    assert_swapped_is_subtype(
        InheritedImplRtProto,
        RtProto,
    )
    # we checks only methods name
    assert_swapped_is_subtype(
        InheritedBadImplRtProto,
        RtProto,
    )

    with pytest.raises(ValueError):
        is_subtype(InheritedImplProto, Proto)

    with pytest.raises(ValueError):
        is_subtype(InheritedBadImplProto, Proto)

    # It is a consequence of builtin runtime_checkable limited behaviour
    assert is_subtype(
        ProtoAttr,
        RtProto
    )

    assert not is_subtype(
        OtherRtProto,
        RtProto
    )
    assert not is_subtype(
        OtherProto,
        RtProto
    )


@has_typed_dict
def test_typed_dict():
    from typing import TypedDict

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

    assert_swapped_is_subtype(
        TDSmall,
        TDBig,
    )

    assert_swapped_is_subtype(
        TDSmallUT,
        TDBigUT,
    )

    # we repeat behavior of PyCharm and MyPy
    assert not is_subtype(TDBigUT, TDSmall)
    assert not is_subtype(TDSmall, TDBigUT)

    assert not is_subtype(TDBig, TDSmallUT)
    assert not is_subtype(TDSmallUT, TDBig)

    assert not is_subtype(TDSmallUT, dict)
    assert not is_subtype(dict, TDSmallUT)

    assert not is_subtype(TDSmall, dict)
    assert not is_subtype(dict, TDSmall)
