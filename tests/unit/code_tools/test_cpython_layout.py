import ctypes
import sys
from dataclasses import FrozenInstanceError, replace

import pytest

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout, select_cpython_layout
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform


def select(version, **changes):
    options = {
        "implementation": "cpython", "system": "linux", "architecture": "x86_64",
        "pointer_size": 8, "special_build": False,
    }
    options.update(changes)
    return select_cpython_layout(version, **options)


@pytest.mark.parametrize("version", [(3, 10), (3, 11), (3, 12), (3, 13), (3, 14)])
def test_layout_selection(version):
    layout = select(version)
    assert layout.version == version
    assert layout is select(version)
    with pytest.raises(FrozenInstanceError):
        layout.object_type = -1


@pytest.mark.parametrize("version", [(3, 9), (3, 15), (4, 0)])
def test_unknown_version_has_no_layout(version):
    assert select(version) is None


@pytest.mark.parametrize("changes", [
    {"implementation": "pypy"}, {"system": "win32"}, {"system": "darwin"},
    {"architecture": "aarch64"}, {"pointer_size": 4}, {"special_build": True},
])
def test_incompatible_build_has_no_layout(changes):
    assert select((3, 14), **changes) is None


def native_layout():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))
    layout = get_cpython_layout()
    if layout is None:
        pytest.skip("No layout for this CPython build")
    return layout


def test_running_sequence_layout_matches_objects():
    layout = native_layout()
    items = [object(), object()]
    value = tuple(items)
    assert ctypes.c_void_p.from_address(id(value) + layout.object_type).value == id(tuple)
    assert ctypes.c_ssize_t.from_address(id(value) + layout.var_size).value == len(value)
    assert ctypes.c_void_p.from_address(id(value) + layout.tuple_items).value == id(value[0])
    array = ctypes.c_void_p.from_address(id(items) + layout.list_items).value
    assert ctypes.c_void_p.from_address(array).value == id(items[0])
    assert ctypes.c_ssize_t.from_address(id(items) + layout.list_allocated).value >= len(items)


def test_tuple_offset_changes_with_version():
    assert select((3, 13)).tuple_items != select((3, 14)).tuple_items


def test_compiler_uses_selected_layout(monkeypatch):
    layout = native_layout()
    from adaptix._internal.code_tools import x86_64_compiler

    # This test inspects code without executing the deliberately altered ABI.
    altered = replace(layout, object_type=layout.object_type + 8)
    monkeypatch.setattr(x86_64_compiler, "get_cpython_layout", lambda: altered)
    compiler = X86Compiler("layout_selection")
    assert not compiler.has_validated_object_header
    assert compiler.layout is altered
    result = compiler.call(lambda value: value, compiler.data)
    convert = compiler.finish(result).make_callable()
    value = object()
    assert convert(value) is value


def test_list_operations_fall_back_without_layout(monkeypatch):
    native_layout()
    from adaptix._internal.code_tools import x86_64_compiler

    monkeypatch.setattr(x86_64_compiler, "get_cpython_layout", lambda: None)
    compiler = X86Compiler("layout_fallback")
    result = compiler.reserve_list(compiler.constant(2))
    element = compiler.copy_reference(compiler.data)
    compiler.append_list(result, element)
    copied = compiler.copy_list(result)
    convert = compiler.finish(copied).make_callable()
    value = object()
    references = sys.getrefcount(value)
    for _ in range(100):
        assert convert(value) == [value]
    assert sys.getrefcount(value) == references


def test_interpreter_evaluator_offset_matches_c_api():
    layout = native_layout()
    if layout.interpreter_eval_frame is None:
        pytest.skip("No interpreter layout for this CPython version")
    from adaptix._internal.code_tools.native_constructor import interpreter_eval_offset

    offset = interpreter_eval_offset()
    assert offset is None or offset == layout.interpreter_eval_frame
