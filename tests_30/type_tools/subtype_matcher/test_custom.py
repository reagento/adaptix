import itertools
from typing import (
    Any, Union, Generic, TypeVar
)

import pytest

from .conftest import (
    match, is_subtype, assert_swapped_is_subtype, Class, SubClass
)


T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)
T_inv = TypeVar('T_inv')


class GenCo(Generic[T_co]):
    pass


class GenContra(Generic[T_contra]):
    pass


class GenInv(Generic[T_inv]):
    pass


@pytest.mark.parametrize(
    'tp',
    [GenCo, GenContra, GenInv]
)
def test_generic_default(tp: Any):
    assert is_subtype(
        tp,
        tp,
    )
    assert_swapped_is_subtype(
        tp[int],
        tp,
    )


def test_generic_match():
    assert match(
        GenCo[int], GenCo[T_co]
    ) == {T_co: int}

    assert match(
        GenContra[int], GenContra[T_contra]
    ) == {T_contra: int}

    assert match(
        GenInv[int], GenInv[T_inv]
    ) == {T_inv: int}


def test_generic():
    assert_swapped_is_subtype(
        GenCo[bool],
        GenCo[int],
    )
    assert_swapped_is_subtype(
        GenContra[int],
        GenContra[bool],
    )
    assert not is_subtype(
        GenInv[int],
        GenInv[bool],
    )
    assert not is_subtype(
        GenInv[bool],
        GenInv[int],
    )

    class AllGen(Generic[T_co, T_contra, T_inv]):
        pass

    assert is_subtype(
        AllGen[int, bool, int],
        AllGen[int, bool, int],
    )

    assert_swapped_is_subtype(
        AllGen[bool, int, int],
        AllGen[int, bool, int],
    )

    assert not is_subtype(
        AllGen[bool, int, int],
        AllGen[int, bool, int],
    )

    variants = [[int, bool]] * 6

    for a1, b1, c1, a2, b2, c2 in itertools.product(*variants):
        if (
            [a1, b1, c1] == [bool, int, int]
            and
            [a2, b2, c2] == [int, bool, int]
        ):
            assert match(
                AllGen[a1, b1, c1],
                AllGen[a2, b2, c2],
            ) == {}

        else:

            assert not is_subtype(
                AllGen[a1, b1, c1],
                AllGen[a2, b2, c2],
            )


B_co = TypeVar('B_co', bound=Class, covariant=True)
B_contra = TypeVar('B_contra', bound=Class, contravariant=True)
B_inv = TypeVar('B_inv', bound=Class)


class BGenCo(Generic[B_co]):
    pass


class BGenContra(Generic[B_contra]):
    pass


class BGenInv(Generic[B_inv]):
    pass


@pytest.mark.parametrize(
    'tp',
    [BGenCo, BGenContra, BGenInv]
)
def test_generic_default_bound(tp: Any):
    assert is_subtype(
        tp,
        tp,
    )
    assert_swapped_is_subtype(
        tp[Class],
        tp,
    )
    assert not is_subtype(
        tp[int],
        tp[bool],
    )
    assert not is_subtype(
        tp[bool],
        tp[int],
    )
    assert not is_subtype(
        tp,
        tp[int],
    )
    assert not is_subtype(
        tp[int],
        tp,
    )


def test_generic_bound():
    assert_swapped_is_subtype(
        BGenCo[SubClass],
        BGenCo[Class],
    )
    assert_swapped_is_subtype(
        BGenContra[Class],
        BGenContra[SubClass],
    )
    assert not is_subtype(
        BGenInv[Class],
        BGenInv[SubClass],
    )
    assert not is_subtype(
        BGenInv[SubClass],
        BGenInv[Class],
    )


TVConstr = TypeVar('TVConstr', int, str, covariant=True)


class GenTVC(Generic[TVConstr]):
    pass


def test_generic_constraints():
    assert is_subtype(
        GenTVC,
        GenTVC,
    )

    assert_swapped_is_subtype(
        GenTVC[int],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[bool],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[str],
        GenTVC,
    )

    assert_swapped_is_subtype(
        GenTVC[Union[str, int]],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[Union[int, str]],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[Union[bool, str]],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[Union[bool, int]],
        GenTVC,
    )
    assert_swapped_is_subtype(
        GenTVC[Union[bool, int, str]],
        GenTVC,
    )

    assert_swapped_is_subtype(
        GenTVC[bool],
        GenTVC[int],
    )

    assert not is_subtype(
        GenTVC[bool],
        GenTVC[str],
    )
    assert not is_subtype(
        GenTVC[str],
        GenTVC[bool],
    )
