from dataclasses import FrozenInstanceError, replace

import pytest

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout, select_cpython_layout
from adaptix._internal.code_tools.cpython_layout.validation import (
    CHECKS,
    COVERED_OFFSETS,
    available_offset_names,
    layout_mismatches,
    validate_layout,
)


def select(version, **changes):
    options = {
        "implementation": "cpython", "system": "linux", "architecture": "x86_64",
        "pointer_size": 8, "special_build": False,
    }
    options.update(changes)
    return select_cpython_layout(version, **options)


@pytest.mark.parametrize("version", [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14), (3, 15)])
def test_layout_selection(version):
    layout = select(version)
    assert layout.version == version
    assert layout is select(version)
    with pytest.raises(FrozenInstanceError):
        layout.object_type = -1


@pytest.mark.parametrize("version", [(3, 9), (3, 16), (4, 0)])
def test_unknown_version_has_no_layout(version):
    assert select(version) is None


def test_required_offset_checks_availability():
    layout = select((3, 10))
    assert layout.offset("object_type") == layout.object_type
    with pytest.raises(RuntimeError, match="type_version"):
        layout.offset("type_version")
    with pytest.raises(RuntimeError, match="unknown_offset"):
        layout.offset("unknown_offset")
    with pytest.raises(TypeError, match="version"):
        layout.offset("version")




@pytest.mark.parametrize("changes", [
    {"implementation": "pypy"}, {"system": "win32"}, {"system": "darwin"},
    {"architecture": "aarch64"}, {"pointer_size": 4}, {"special_build": True},
    {"release_level": "alpha"}, {"release_level": "beta"}, {"release_level": "candidate"},
])
def test_incompatible_build_has_no_layout(changes):
    assert select((3, 14), **changes) is None






def test_tuple_offset_changes_with_version():
    assert select((3, 13)).tuple_items != select((3, 14)).tuple_items












def test_running_interpreter_matches_its_layout():
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    assert sorted(layout_mismatches(layout)) == []


def test_every_available_offset_is_covered():
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    assert sorted(available_offset_names(layout) - COVERED_OFFSETS) == []


def test_validation_runs_every_applicable_check():
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    available = available_offset_names(layout)
    expected = {
        name
        for names, _ in CHECKS
        if all(name in available for name in names)
        for name in names
    }
    assert set(validate_layout(layout)) == expected


@pytest.mark.parametrize("version", [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14), (3, 15)])
def test_declared_offsets_are_covered_for_every_version(version):
    layout = select(version)
    assert sorted(available_offset_names(layout) - COVERED_OFFSETS) == []


@pytest.mark.parametrize(
    "field",
    [
        "object_type", "tuple_items", "list_items", "set_used", "type_flags", "dict_used",
        "unicode_entry_value", "values_items", "unicode_hash", "bytes_data", "long_digits",
        "set_table", "member_offset", "function_code", "cell_contents", "thread_interpreter",
        "datetime_tzinfo", "time_tzinfo", "timedelta_seconds", "timezone_offset",
        "dictiter_dict", "abc_negative_cache",
    ],
)
def test_corrupted_offset_is_reported(field):
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    if getattr(layout, field) is None:
        pytest.skip(f"CPython {layout.version} has no {field} offset")
    siblings = [
        getattr(layout, other)
        for names, _ in CHECKS if field in names
        for other in names
        if other != field and getattr(layout, other) is not None
        and getattr(layout, other) != getattr(layout, field)
    ]
    corrupted = replace(layout, **{field: siblings[0] if siblings else getattr(layout, field) + 8})
    assert field in layout_mismatches(corrupted)
