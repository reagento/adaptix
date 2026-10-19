import sys
from dataclasses import MISSING, FrozenInstanceError, fields, replace

import pytest

from adaptix._internal.code_tools.cpython_layout.definitions import CPythonLayout
from adaptix._internal.code_tools.cpython_layout.selection import (
    LAYOUTS,
    PRERELEASE_LAYOUT_ENV_VAR,
    get_cpython_layout,
    prerelease_layout_allowed,
    select_cpython_layout,
)
from adaptix._internal.code_tools.cpython_layout.validation import (
    CHECKS,
    COVERED_OFFSETS,
    UNVERIFIABLE_OFFSETS,
    available_offset_names,
    layout_matches_interpreter,
    layout_mismatches,
    validate_layout,
)

SUPPORTED_VERSIONS = [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14), (3, 15)]


def select(version, **changes):
    options = {
        "implementation": "cpython", "system": "linux", "architecture": "x86_64",
        "pointer_size": 8, "special_build": False,
    }
    options.update(changes)
    return select_cpython_layout(version, **options)


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_layout_selection(version):
    layout = select(version)
    assert layout.version == version
    assert layout is select(version)
    with pytest.raises(FrozenInstanceError):
        layout.object_type = -1


@pytest.mark.parametrize("version", [(3, 9), (3, 16), (4, 0)])
def test_unknown_version_has_no_layout(version):
    assert select(version) is None


def test_absent_capability_groups_raise_on_request():
    oldest = select((3, 10))
    with pytest.raises(RuntimeError, match="dictionary keys"):
        oldest.require_dict_keys()
    with pytest.raises(RuntimeError, match="inline values"):
        oldest.require_inline_values()
    with pytest.raises(RuntimeError, match="integer"):
        oldest.require_long()

    newest = select((3, 13))
    assert newest.require_dict_keys() is newest.dict_keys_layout
    assert newest.require_inline_values() is newest.inline_values
    assert newest.require_long() is newest.long_layout


@pytest.mark.parametrize(
    ["field", "first_version"],
    [
        ("object_type", (3, 10)),
        ("type_version", (3, 10)),
        ("datetime_data", (3, 10)),
        ("timezone_offset", (3, 10)),
        ("thread_eval_breaker", (3, 13)),
    ],
)
@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_offset_availability_follows_the_structure_history(field, first_version, version):
    present = getattr(select(version), field) is not None
    assert present == (version >= first_version)


@pytest.mark.parametrize(
    ["group", "first_version"],
    [
        ("dict_keys_layout", (3, 11)),
        ("long_layout", (3, 12)),
        ("inline_values", (3, 13)),
    ],
)
@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_capability_groups_follow_the_structure_history(group, first_version, version):
    present = getattr(select(version), group) is not None
    assert present == (version >= first_version)


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


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_declared_offsets_are_covered_for_every_version(version):
    layout = select(version)
    assert sorted(available_offset_names(layout) - COVERED_OFFSETS) == []


def read_offset(layout, name):
    if "." not in name:
        return getattr(layout, name)
    group, member = name.split(".", 1)
    container = getattr(layout, group)
    return None if container is None else getattr(container, member)


def with_offset(layout, name, value):
    if "." not in name:
        return replace(layout, **{name: value})
    group, member = name.split(".", 1)
    return replace(layout, **{group: replace(getattr(layout, group), **{member: value})})


@pytest.mark.parametrize(
    "field",
    [
        "object_type", "tuple_items", "list_items", "set_used", "type_flags", "dict_used",
        "dict_keys_layout.unicode_entry_value", "inline_values.items", "unicode_hash", "bytes_data",
        "long_layout.digits", "set_table", "member_offset", "function_code", "cell_contents",
        "thread_interpreter", "datetime_tzinfo", "time_tzinfo", "timedelta_seconds", "timezone_offset",
        "dictiter_dict", "abc_negative_cache",
    ],
)
def test_corrupted_offset_is_reported(field):
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    if read_offset(layout, field) is None:
        pytest.skip(f"CPython {layout.version} has no {field} offset")
    original = read_offset(layout, field)
    siblings = [
        read_offset(layout, other)
        for names, _ in CHECKS if field in names
        for other in names
        if other != field and read_offset(layout, other) is not None
        and read_offset(layout, other) != original
    ]
    corrupted = with_offset(layout, field, siblings[0] if siblings else original + 8)
    assert field in layout_mismatches(corrupted)


def test_offsets_available_everywhere_are_not_optional():
    optional = [
        name for name, field in CPythonLayout.__dataclass_fields__.items()
        if field.default is None
    ]
    always_available = [
        name for name in optional
        if all(getattr(select(version), name) is not None for version in SUPPORTED_VERSIONS)
    ]
    assert always_available == []


def test_capability_groups_have_no_optional_members():
    groups = [CPythonLayout.__dataclass_fields__[name].type for name in ("dict_keys_layout", "inline_values", "long_layout")]
    assert [group for group in groups if "None" not in str(group)] == []
    for name in ("dict_keys_layout", "inline_values", "long_layout"):
        group = getattr(select((3, 13)), name)
        assert [field for field in fields(group) if field.default is not MISSING] == []


@pytest.mark.parametrize("level", ["alpha", "beta", "candidate"])
def test_prerelease_needs_the_opt_in(level):
    assert select((3, 15), release_level=level) is None
    assert select((3, 15), release_level=level, allow_prerelease=True) is not None
    assert select((3, 16), release_level=level, allow_prerelease=True) is None


@pytest.mark.parametrize(
    ["value", "allowed"],
    [("1", True), ("0", False), ("", False), ("true", False), ("yes", False), (None, False)],
)
def test_prerelease_env_var_accepts_only_one(monkeypatch, value, allowed):
    if value is None:
        monkeypatch.delenv(PRERELEASE_LAYOUT_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(PRERELEASE_LAYOUT_ENV_VAR, value)
    assert prerelease_layout_allowed() is allowed


def test_matching_interpreter_is_recognised():
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    assert layout_matches_interpreter(layout)
    assert not layout_matches_interpreter(with_offset(layout, "timezone_offset", layout.timezone_size))


class FakeVersionInfo(tuple):
    __slots__ = ()

    def __new__(cls, version, release_level):
        return super().__new__(cls, (*version, 0, release_level, 0))

    @property
    def releaselevel(self):
        return self[3]


@pytest.fixture
def uncached_layout():
    get_cpython_layout.cache_clear()
    yield
    get_cpython_layout.cache_clear()


def test_prerelease_opt_in_is_refused_when_offsets_moved(monkeypatch, uncached_layout):
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    monkeypatch.setenv(PRERELEASE_LAYOUT_ENV_VAR, "1")
    monkeypatch.setattr(sys, "version_info", FakeVersionInfo(layout.version, "candidate"))

    get_cpython_layout.cache_clear()
    monkeypatch.setitem(LAYOUTS, layout.version, layout)
    assert get_cpython_layout() is layout

    get_cpython_layout.cache_clear()
    monkeypatch.setitem(LAYOUTS, layout.version, with_offset(layout, "timezone_offset", layout.timezone_size))
    assert get_cpython_layout() is None


def test_every_available_offset_is_probed_on_this_interpreter():
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No CPython layout is available for this interpreter build")
    probed = set(validate_layout(layout))
    expected = available_offset_names(layout) - UNVERIFIABLE_OFFSETS
    assert sorted(expected - probed) == []
