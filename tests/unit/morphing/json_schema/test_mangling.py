import pytest

from adaptix._internal.morphing.json_schema.definitions import JSONSchema, LocalRefSource
from adaptix._internal.morphing.json_schema.mangling import CompoundRefMangler, IndexRefMangler, QualnameRefMangler
from adaptix._internal.morphing.json_schema.resolver import LocalRefSourceGroup
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.location import TypeHintLoc


def make_group(*types, pinned=None):
    sources = [
        LocalRefSource(value=pinned, json_schema=JSONSchema(), loc_stack=LocStack(TypeHintLoc(tp)))
        for tp in types
    ]
    return LocalRefSourceGroup(sources)


class _Outer:
    class _Inner:
        pass


@pytest.mark.parametrize(
    ["kwargs", "expected_g1", "expected_g2"],
    [
        ({}, "Foo-1", "Foo-2"),
        ({"start": 0}, "Foo-0", "Foo-1"),
        ({"separator": "."}, "Foo.1", "Foo.2"),
    ],
)
def test_index_mangler_two_groups(kwargs, expected_g1, expected_g2):
    g1, g2 = make_group(int), make_group(str)

    result = IndexRefMangler(**kwargs).mangle_refs((), "Foo", [g1, g2])

    assert result == {g1: expected_g1, g2: expected_g2}


def test_index_mangler_three_groups():
    g1, g2, g3 = make_group(int), make_group(str), make_group(float)

    result = IndexRefMangler().mangle_refs((), "T", [g1, g2, g3])

    assert result == {g1: "T-1", g2: "T-2", g3: "T-3"}


def test_index_mangler_skips_occupied_ref():
    g1, g2 = make_group(int), make_group(str)

    result = IndexRefMangler().mangle_refs(("Foo-1",), "Foo", [g1, g2])

    assert result == {g1: "Foo-2", g2: "Foo-3"}


def test_index_mangler_skips_multiple_occupied_refs():
    g1 = make_group(int)

    result = IndexRefMangler().mangle_refs(("Foo-1", "Foo-2", "Foo-3"), "Foo", [g1])

    assert result == {g1: "Foo-4"}


def test_qualname_mangler_builtin_types():
    g_int, g_str = make_group(int), make_group(str)

    result = QualnameRefMangler().mangle_refs((), "common", [g_int, g_str])

    assert result == {g_int: "int", g_str: "str"}


def test_qualname_mangler_nested_class():
    g = make_group(_Outer._Inner)

    result = QualnameRefMangler().mangle_refs((), "common", [g])

    assert result == {g: "_Outer._Inner"}


def test_qualname_mangler_mixed_types_in_group_falls_back_to_common_ref():
    g_mixed = LocalRefSourceGroup([
        LocalRefSource(value=None, json_schema=JSONSchema(), loc_stack=LocStack(TypeHintLoc(int))),
        LocalRefSource(value=None, json_schema=JSONSchema(), loc_stack=LocStack(TypeHintLoc(str))),
    ])

    result = QualnameRefMangler().mangle_refs((), "FallbackName", [g_mixed])

    assert result == {g_mixed: "FallbackName"}


def test_qualname_mangler_same_type_multiple_sources_uses_qualname():
    g = LocalRefSourceGroup([
        LocalRefSource(value=None, json_schema=JSONSchema(), loc_stack=LocStack(TypeHintLoc(int))),
        LocalRefSource(value=None, json_schema=JSONSchema(), loc_stack=LocStack(TypeHintLoc(int))),
    ])

    result = QualnameRefMangler().mangle_refs((), "common", [g])

    assert result == {g: "int"}


def test_compound_mangler_no_conflict_uses_base_result():
    g_int, g_str = make_group(int), make_group(str)
    cm = CompoundRefMangler(QualnameRefMangler(), IndexRefMangler())

    result = cm.mangle_refs((), "common", [g_int, g_str])

    assert result == {g_int: "int", g_str: "str"}


def test_compound_mangler_conflict_appends_index_suffix():
    g1, g2 = make_group(int), make_group(int)
    cm = CompoundRefMangler(QualnameRefMangler(), IndexRefMangler())

    result = cm.mangle_refs((), "common", [g1, g2])

    assert result == {g1: "int-1", g2: "int-2"}


def test_compound_mangler_partial_conflict_leaves_unique_refs_unchanged():
    g_int1, g_int2, g_str = make_group(int), make_group(int), make_group(str)
    cm = CompoundRefMangler(QualnameRefMangler(), IndexRefMangler())

    result = cm.mangle_refs((), "common", [g_int1, g_int2, g_str])

    assert result == {g_int1: "int-1", g_int2: "int-2", g_str: "str"}


@pytest.mark.parametrize(
    ["start", "separator", "expected_g1", "expected_g2"],
    [
        (1, "-", "int-1", "int-2"),
        (0, "_", "int_0", "int_1"),
    ],
)
def test_compound_mangler_wrapper_params_propagate(start, separator, expected_g1, expected_g2):
    g1, g2 = make_group(int), make_group(int)
    cm = CompoundRefMangler(QualnameRefMangler(), IndexRefMangler(start=start, separator=separator))

    result = cm.mangle_refs((), "common", [g1, g2])

    assert result == {g1: expected_g1, g2: expected_g2}
