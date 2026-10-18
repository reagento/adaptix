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


def test_missing_native_api_is_unavailable(monkeypatch):
    from adaptix._internal.code_tools.native_access import api, api_address

    assert api_address("AdaptixMissingEntryPoint") is None
    assert api("AdaptixMissingEntryPoint", ctypes.c_void_p) is None
    monkeypatch.delattr(ctypes, "pythonapi", raising=False)
    assert api_address("PyType_GetSlot") is None
    assert api("PyType_GetSlot", ctypes.c_void_p) is None


@pytest.mark.parametrize("changes", [
    {"implementation": "pypy"}, {"system": "win32"}, {"system": "darwin"},
    {"architecture": "aarch64"}, {"pointer_size": 4}, {"special_build": True},
    {"release_level": "alpha"}, {"release_level": "beta"}, {"release_level": "candidate"},
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


def test_native_platform_requires_a_supported_layout(monkeypatch):
    native_layout()
    from adaptix._internal.code_tools.cpython_layout import selection

    monkeypatch.setattr(selection, "get_cpython_layout", lambda: None)
    with pytest.raises(RuntimeError, match="No CPython layout"):
        check_native_platform()


def test_object_header_validation_with_materialized_frame_locals():
    native_layout()
    from adaptix._internal.code_tools.x86_64_compiler import inline_refcount_mode

    def observe(frame, event, arg):
        if frame.f_code is inline_refcount_mode.__code__:
            frame.f_locals.get("probe")
        return observe

    previous = sys.gettrace()
    sys.settrace(observe)
    try:
        assert inline_refcount_mode() is not None
    finally:
        sys.settrace(previous)


def test_interpreter_evaluator_offset_matches_c_api():
    layout = native_layout()
    if layout.interpreter_eval_frame is None:
        pytest.skip("No interpreter layout for this CPython version")
    from adaptix._internal.code_tools.native_constructor import interpreter_eval_offset

    offset = interpreter_eval_offset()
    assert offset is None or offset == layout.interpreter_eval_frame
