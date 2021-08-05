import itertools
from typing import (
    Any, Union, Generic, TypeVar
)

import pytest

from .conftest import matcher, assert_subtype_shift, Class, SubClass


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
    assert matcher.is_subtype(
        tp,
        tp,
    )
    assert_subtype_shift(
        tp[int],
        tp,
    )


def test_generic_match():
    assert matcher(
        GenCo[T_co], GenCo[int]
    ) == {T_co: int}

    assert matcher(
        GenContra[T_contra], GenContra[int]
    ) == {T_contra: int}

    assert matcher(
        GenInv[T_inv], GenInv[int]
    ) == {T_inv: int}


def test_generic():
    assert_subtype_shift(
        GenCo[bool],
        GenCo[int],
    )
    assert_subtype_shift(
        GenContra[int],
        GenContra[bool],
    )
    assert not matcher.is_subtype(
        GenInv[int],
        GenInv[bool],
    )
    assert not matcher.is_subtype(
        GenInv[bool],
        GenInv[int],
    )

    class AnyGen(Generic[T_co, T_contra, T_inv]):
        pass

    assert matcher.is_subtype(
        AnyGen[int, bool, int],
        AnyGen[int, bool, int],
    )

    assert_subtype_shift(
        AnyGen[bool, int, int],
        AnyGen[int, bool, int],
    )

    assert not matcher.is_subtype(
        AnyGen[bool, int, int],
        AnyGen[int, bool, int],
    )

    variants = [[int, bool]] * 6

    for a1, b1, c1, a2, b2, c2 in itertools.product(*variants):
        if (
            [a1, b1, c1] == [bool, int, int]
            and
            [a2, b2, c2] == [int, bool, int]
        ):
            assert matcher(
                AnyGen[a1, b1, c1],
                AnyGen[a2, b2, c2],
            ) == {}

        else:

            assert not matcher.is_subtype(
                AnyGen[a1, b1, c1],
                AnyGen[a2, b2, c2],
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
    assert matcher.is_subtype(
        tp,
        tp,
    )
    assert_subtype_shift(
        tp[Class],
        tp,
    )
    assert not matcher.is_subtype(
        tp[int],
        tp[bool],
    )
    assert not matcher.is_subtype(
        tp[bool],
        tp[int],
    )
    assert not matcher.is_subtype(
        tp,
        tp[int],
    )
    assert not matcher.is_subtype(
        tp[int],
        tp,
    )


def test_generic_bound():
    assert_subtype_shift(
        GenCo[SubClass],
        GenCo[Class],
    )
    assert_subtype_shift(
        GenContra[Class],
        GenContra[SubClass],
    )
    assert not matcher.is_subtype(
        GenInv[Class],
        GenInv[SubClass],
    )
    assert not matcher.is_subtype(
        GenInv[SubClass],
        GenInv[Class],
    )


TVConstr = TypeVar('TVConstr', int, str, covariant=True)


class GenTVC(Generic[TVConstr]):
    pass


def test_generic_constraints():
    assert matcher.is_subtype(
        GenTVC,
        GenTVC,
    )

    assert_subtype_shift(
        GenTVC[int],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[bool],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[str],
        GenTVC,
    )

    assert_subtype_shift(
        GenTVC[Union[str, int]],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[Union[int, str]],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[Union[bool, str]],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[Union[bool, int]],
        GenTVC,
    )
    assert_subtype_shift(
        GenTVC[Union[bool, int, str]],
        GenTVC,
    )

    assert_subtype_shift(
        GenTVC[bool],
        GenTVC[int],
    )

    assert not matcher.is_subtype(
        GenTVC[bool],
        GenTVC[str],
    )
    assert not matcher.is_subtype(
        GenTVC[str],
        GenTVC[bool],
    )

