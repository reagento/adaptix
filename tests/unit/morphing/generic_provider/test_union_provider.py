from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Literal, Optional, Union

import pytest
from tests_helpers import raises_exc, with_cause, with_notes

from adaptix import CannotProvide, DebugTrail, ProviderNotFoundError, Retort, dumper, loader
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.morphing.load_error import BadVariantLoadError, LoadError, TypeLoadError, UnionLoadError
from adaptix._internal.type_tools import normalize_type


def _norm_union_tp(tp):
    # Due to caching inside normalize_type,
    # it can change the order of elements inside Union typehint
    # when it fetched by `.source` attribute.
    # It will fail string representation test, this function fixes this
    return normalize_type(tp).source


def test_loading(strict_coercion, debug_trail):
    union_tp = _norm_union_tp(Union[int, str])
    retort = Retort()
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        union_tp,
    )

    assert loader_(1) == 1
    assert loader_("a") == "a"

    if not strict_coercion:
        return

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            LoadError(),
            lambda: loader_([]),
        )
    elif debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
        raises_exc(
            UnionLoadError(
                f"while loading {union_tp}",
                [
                    TypeLoadError(int, []),
                    TypeLoadError(str, []),
                ],
            ),
            lambda: loader_([]),
        )


def bad_string_loader(data):
    if isinstance(data, str):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def bad_int_loader(data):
    if isinstance(data, int):
        return data
    raise TypeError  # must raise LoadError instance (TypeLoadError)


def test_loading_unexpected_error(strict_coercion, debug_trail):
    union_tp = _norm_union_tp(Union[int, str])
    retort = Retort()
    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).extend(
        recipe=[
            loader(str, bad_string_loader),
            loader(int, bad_int_loader),
        ],
    ).get_loader(
        union_tp,
    )

    if debug_trail in (DebugTrail.DISABLE, DebugTrail.FIRST):
        raises_exc(
            TypeError(),
            lambda: loader_([]),
        )
    elif debug_trail == DebugTrail.ALL:
        raises_exc(
            CompatExceptionGroup(
                f"while loading {union_tp}",
                [
                    TypeError(),
                    TypeError(),
                ],
            ),
            lambda: loader_([]),
        )


def test_dumping(debug_trail):
    retort = Retort()
    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[int, str],
    )

    assert dumper_(1) == 1
    assert dumper_("a") == "a"


def test_dumping_of_none(debug_trail):
    retort = Retort()
    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[int, str, None],
    )

    assert dumper_(1) == 1
    assert dumper_("a") == "a"
    assert dumper_(None) is None


def test_dumping_subclass(debug_trail):
    @dataclass
    class Parent:
        foo: int

    @dataclass
    class Child(Parent):
        bar: int

    dumper_ = Retort(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[Parent, str],
    )

    assert dumper_(Parent(foo=1)) == {"foo": 1}
    assert dumper_(Child(foo=1, bar=2)) == {"foo": 1}
    assert dumper_("a") == "a"

    raises_exc(
        KeyError(list),
        lambda: dumper_([]),
    )


def test_optional_dumping(debug_trail):
    retort = Retort()
    opt_dumper = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Optional[str],
    )

    assert opt_dumper("a") == "a"
    assert opt_dumper(None) is None


def test_bad_optional_dumping(debug_trail):
    retort = Retort()
    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce dumper for type {Union[int, Callable[[int], str]]}",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            with_notes(
                CannotProvide(
                    message=f"All cases of union must be class or Literal, but found {[Callable[[int], str]]}",
                    is_demonstrative=True,
                    is_terminal=True,
                ),
                f"Location: `{str(Union[int, Callable[[int], str]]).replace('typing.', '', 1)}`",
            ),
        ),
        lambda: (
            retort.replace(
                debug_trail=debug_trail,
            ).extend(
                recipe=[
                    dumper(Callable[[int], str], lambda x: str(x)),
                ],
            ).get_dumper(
                Union[int, Callable[[int], str]],
            )
        ),
    )


def test_literal(strict_coercion, debug_trail):
    retort = Retort()

    loader_ = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    ).get_loader(
        Literal["a", None],
    )

    assert loader_("a") == "a"
    assert loader_(None) is None

    if debug_trail == DebugTrail.DISABLE:
        raises_exc(
            BadVariantLoadError({"a"}, "b"),
            lambda: loader_("b"),
        )
    elif debug_trail in (DebugTrail.FIRST, DebugTrail.ALL):
        raises_exc(
            UnionLoadError(
                f'while loading {Literal["a", None]}',
                [TypeLoadError(None, "b"), BadVariantLoadError({"a"}, "b")],
            ),
            lambda: loader_("b"),
        )

    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Literal["a", None],
    )

    assert dumper_("a") == "a"
    assert dumper_(None) is None
    assert dumper_("b") == "b"


@pytest.mark.parametrize(
    ["other_type", "value", "expected", "wrong_value"],
    [
        (
         Decimal, Decimal("200.5"), "200.5", [1, 2, 3],
        ),
        (
         Union[str, Decimal], "some string", "some string", [1, 2, 3],
        ),
    ],
)
def test_dump_literal_in_union(
    strict_coercion,
    debug_trail,
    other_type,
    value,
    expected,
    wrong_value,
):
    retort = Retort()

    dumper_ = retort.replace(
        debug_trail=debug_trail,
    ).get_dumper(
        Union[Literal[200, 300], other_type],
    )

    assert dumper_(200) == 200
    assert dumper_(300) == 300
    assert dumper_(value) == expected

    with pytest.raises(KeyError):
        dumper_(wrong_value)
