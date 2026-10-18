from dataclasses import FrozenInstanceError

import pytest

from adaptix._internal.code_tools.cpython_layout.selection import select_cpython_layout


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










