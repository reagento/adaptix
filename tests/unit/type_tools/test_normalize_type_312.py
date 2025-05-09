from typing import TypeVar

from adaptix._internal.common import VarTuple
from adaptix._internal.type_tools import normalize_type
from adaptix._internal.type_tools.normalize_type import AnyNormTypeVarLike, NormTypeAlias

from .local_helpers import assert_strict_equal, nt_zero


def _norm_type_vars(alias) -> VarTuple[AnyNormTypeVarLike]:
    return tuple(normalize_type(type_var) for type_var in alias.__type_params__)


def test_type_alias_syntax_simple():
    type MyAlias = int

    assert_strict_equal(
        normalize_type(MyAlias),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias,
        ),
    )


def test_type_alias_syntax_recursive():
    type MyAlias = list[MyAlias]

    assert_strict_equal(
        normalize_type(MyAlias),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias,
        ),
    )


def test_type_alias_syntax_type_var():
    type MyAlias[T] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias,
        ),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(nt_zero(int), ),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[int],
        ),
    )

    T2 = TypeVar("T2")
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(normalize_type(T2),),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[T2],
        ),
    )


def test_type_alias_syntax_type_var_bound():
    type MyAlias[T: int] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias,
        ),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(nt_zero(int), ),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[int],
        ),
    )
    T2 = TypeVar("T2")
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(normalize_type(T2),),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[T2],
        ),
    )


def test_type_alias_syntax_type_var_constraints():
    type MyAlias[T: (int, str)] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias,
        ),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(nt_zero(int), ),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[int],
        ),
    )
    T2 = TypeVar("T2")
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        NormTypeAlias(
            type_alias=MyAlias,
            args=(normalize_type(T2),),
            type_vars=_norm_type_vars(MyAlias),
            source=MyAlias[T2],
        ),
    )
