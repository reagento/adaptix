from typing import TypeAliasType, TypeVar

from adaptix._internal.type_tools import normalize_type
from adaptix._internal.type_tools.normalize_type import AnyNormTypeVarLike, NormTypeAlias

from .local_helpers import assert_strict_equal, nt_zero


def test_type_alias_syntax_simple():
    type MyAlias = int

    assert_strict_equal(
        normalize_type(MyAlias),
        _make_type_alias(MyAlias, []),
    )


def test_type_alias_syntax_recursive():
    type MyAlias = list[MyAlias]

    assert_strict_equal(
        normalize_type(MyAlias),
        _make_type_alias(MyAlias, []),
    )


T2 = TypeVar("T2")


def _norm_tp_param(alias: TypeAliasType, idx: int) -> AnyNormTypeVarLike:
    return normalize_type(alias.__type_params__[idx])


def _make_type_alias(alias, args):
    return NormTypeAlias(
        alias,
        args=tuple(args),
        type_vars=tuple(normalize_type(type_var) for type_var in alias.__type_params__),
    )


def test_type_alias_syntax_type_var():
    type MyAlias[T] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        _make_type_alias(MyAlias, []),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        _make_type_alias(MyAlias, [nt_zero(int)]),
    )
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        _make_type_alias(MyAlias, [normalize_type(T2)]),
    )


def test_type_alias_syntax_type_var_bound():
    type MyAlias[T: int] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        _make_type_alias(MyAlias, []),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        _make_type_alias(MyAlias, [nt_zero(int)]),
    )
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        _make_type_alias(MyAlias, [normalize_type(T2)]),
    )


def test_type_alias_syntax_type_var_constraints():
    type MyAlias[T: (int, str)] = list[T]

    assert_strict_equal(
        normalize_type(MyAlias),
        _make_type_alias(MyAlias, []),
    )
    assert_strict_equal(
        normalize_type(MyAlias[int]),
        _make_type_alias(MyAlias, [nt_zero(int)]),
    )
    assert_strict_equal(
        normalize_type(MyAlias[T2]),
        _make_type_alias(MyAlias, [normalize_type(T2)]),
    )
