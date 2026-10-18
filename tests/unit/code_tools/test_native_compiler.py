import ctypes
import gc
import inspect
import random
import sys
import weakref
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from tests_helpers import reference_counts

from adaptix import CodeGenBackend, Retort
from adaptix._internal.code_tools.native_callable import ExecutableMemory
from adaptix._internal.code_tools.native_dictionary import DictionaryTemplate
from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate, Slot, X86Assembler
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform
from adaptix._internal.morphing.native.x86_64.iterable import (
    append_tuple_item,
    finish_tuple_output,
    reserve_iterator_output,
)


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


def test_call_protocol_and_vectorcall():
    compiler = X86Compiler("native_call")
    result = compiler.call(lambda a, b, c: (a, b, c), compiler.data, compiler.constant(2), compiler.constant(3))
    function = compiler.finish(result).make_callable()

    assert function(1) == (1, 2, 3)
    assert function(data=4) == (4, 2, 3)
    assert function(**{bytearray(b"data").decode(): 5}) == (5, 2, 3)
    assert function(6, **{}) == (6, 2, 3)  # noqa: PIE804
    assert str(inspect.signature(function)) == "(data)"
    for args, kwargs in [((), {}), ((1, 2), {}), ((), {"other": 1}), ((1,), {"data": 2})]:
        with pytest.raises(TypeError):
            function(*args, **kwargs)


@pytest.mark.parametrize("arity", [0, 1, 2, 6, 8])
def test_native_positional_and_keyword_signatures(arity):
    names = tuple(f"value{index}" for index in range(arity))
    compiler = X86Compiler("native_signature", parameters=names)
    result = compiler.call(lambda *values: values, *compiler.arguments)
    function = compiler.finish(result).make_callable()
    values = tuple(object() for _ in names)
    assert function(*values) == values
    assert function(**dict(zip(names, values, strict=True))) == values
    assert str(inspect.signature(function)) == "(" + ", ".join(names) + ")"
    outer = X86Compiler("native_outer")
    returned = outer.call(function, *(outer.constant(value) for value in values))
    assert outer.finish(returned).make_callable()(None) == values
    for args, kwargs in [((*values, None), {}), (values, {"unknown": None})]:
        with pytest.raises(TypeError):
            function(*args, **kwargs)
    if values:
        with pytest.raises(TypeError):
            function(*values[:-1])
        with pytest.raises(TypeError):
            function(*values, **{names[0]: None})


def test_native_closures_share_code_and_own_their_context():
    class Context:
        pass

    compiler = X86Compiler("native_closure", parameters=("value",), bound_context=True)
    assert compiler.bound_context is not None
    result = compiler.call(lambda context, value: (context, value), compiler.bound_context, compiler.arguments[0])
    template = compiler.finish(result)
    first_context, second_context = Context(), Context()
    first, second = template.bind(first_context), template.bind(second_context)
    assert first.memory is second.memory is template.memory
    first_callable, second_callable = first.make_callable(), second.make_callable()
    assert first_callable(1) == (first_context, 1)
    assert second_callable(value=2) == (second_context, 2)
    caller = X86Compiler("call_closure")
    result = caller.call(first_callable, caller.data)
    assert caller.finish(result).make_callable()(3) == (first_context, 3)
    reference = weakref.ref(first_context)
    del first_context, first
    gc.collect()
    assert reference() is not None
    assert first_callable(4) == (reference(), 4)
    del first_callable, caller
    gc.collect()
    assert reference() is None
    with pytest.raises(ValueError, match="closure"):
        _ = second.raw_address


def test_native_default_arguments_and_keyword_lifetimes():
    default = object()
    compiler = X86Compiler("native_defaults", parameters=("value", "optional"), defaults=(default,))
    result = compiler.call(lambda *values: values, *compiler.arguments)
    function = compiler.finish(result).make_callable()
    assert function(1) == (1, default)
    assert function(value=2) == (2, default)
    assert function(optional=3, value=4) == (4, 3)
    assert function(5, optional=6) == (5, 6)
    references = sys.getrefcount(default)
    for _ in range(100):
        function(value=object())
    assert sys.getrefcount(default) == references


def test_c_call_reuses_empty_destination_and_cleans_up_on_errors():
    destroyed = []
    result = object()

    class Temporary:
        def __del__(self):
            destroyed.append(True)

    def finish(data):
        if data:
            raise ValueError("destination failure")
        return result

    compiler = X86Compiler("native_c_destination")
    destination = compiler.slot(owned=True)
    assert compiler.call_c(
        "PyObject_CallOneArg", compiler.constant(lambda data: Temporary()), compiler.data, destination=destination,
    ) == destination
    compiler.release(destination)
    assert compiler.call_c(
        "PyObject_CallOneArg", compiler.constant(finish), compiler.data, destination=destination,
    ) == destination
    function = compiler.finish(destination).make_callable()
    references = reference_counts([result])
    for _ in range(100):
        assert function(0) is result
        with pytest.raises(ValueError, match="destination failure"):
            function(1)
    assert len(destroyed) == 200
    assert reference_counts([result]) == references


def test_c_call_destination_requires_owned_object_slot():
    compiler = X86Compiler("native_c_destination_validation")
    with pytest.raises(ValueError, match="owned object slot"):
        compiler.call_c("PyObject_Str", compiler.data, destination=compiler.data)
    with pytest.raises(ValueError, match="owned object slot"):
        compiler.call_c("Py_IncRef", compiler.data, result="void", destination=compiler.slot(owned=True))


def test_injected_assembler_covers_all_fragments_and_preserves_machine_code(monkeypatch):
    def convert(value):
        if value is None:
            raise ValueError("missing")
        return str(value)

    def recover(error):
        return str(error)

    # Share the one allocated literal so absolute pointers in both encodings
    # match. The emitted instructions and their layout can then be compared.
    keyword = ctypes.create_string_buffer(b"data")
    monkeypatch.setattr(ctypes, "create_string_buffer", lambda value: keyword)

    def build(assembler_factory):
        compiler = X86Compiler("injected_assembler", assembler_factory=assembler_factory)
        compiler.function_context("PyThreadState_Get")
        result = compiler.guarded_call(convert, (compiler.data,), recover)
        return compiler.finish(result)

    expected = build(X86Assembler)
    fragments = []

    class InjectedAssembler(X86Assembler):
        def __init__(self):
            super().__init__()
            fragments.append(self)

        def extend(self, other):
            assert isinstance(other, InjectedAssembler)
            super().extend(other)

    def forbidden():
        pytest.fail("Compiler bypassed the injected assembler factory")

    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.X86Assembler", forbidden)
    actual = build(InjectedAssembler)
    assert len(fragments) >= 7  # body, cold, recovery, flow, prefix, unary, context
    assert actual.machine_code == expected.machine_code
    assert actual.assembly == expected.assembly
    function = actual.make_callable()
    assert function(123) == "123"
    assert function(data=456) == "456"
    assert function(None) == "missing"


def test_reference_cleanup_on_success_and_failure():
    value = object()
    compiler = X86Compiler("native_refs")
    copied = compiler.call(lambda x: x, compiler.data)
    result = compiler.call(lambda x: x, copied)
    function = compiler.finish(result).make_callable()
    references = reference_counts([value])

    for _ in range(1000):
        assert function(value) is value
    assert reference_counts([value]) == references

    def fail(data):
        raise ValueError("failure")

    compiler = X86Compiler("native_fail")
    copied = compiler.call(lambda x: x, compiler.data)
    result = compiler.call(fail, copied)
    function = compiler.finish(result).make_callable()
    references = reference_counts([value])
    for _ in range(1000):
        with pytest.raises(ValueError, match="failure"):
            function(value)
    assert reference_counts([value]) == references


def test_guarded_call_preserves_traceback_and_base_exception():
    seen = []

    def fail(value):
        raise value

    def recover(error):
        seen.append(error)
        return 42

    compiler = X86Compiler("native_recover")
    result = compiler.guarded_call(fail, (compiler.data,), recover)
    function = compiler.finish(result).make_callable()
    error = KeyboardInterrupt()
    assert function(error) == 42
    assert seen == [error]
    assert error.__traceback__ is not None
    assert error.__traceback__.tb_frame.f_code.co_name == "fail"


def test_dict_lookup_distinguishes_missing_from_failed_hash():
    class BadKey:
        def __hash__(self):
            raise ValueError("bad hash")

    compiler = X86Compiler("native_lookup")
    result = compiler.dict_lookup(compiler.data, "key", "missing")
    function = compiler.finish(result).make_callable()
    assert function({"key": 12}) == 12
    assert function({}) == "missing"

    compiler = X86Compiler("native_lookup_error")
    result = compiler.dict_lookup(compiler.data, BadKey(), None)
    function = compiler.finish(result).make_callable()
    with pytest.raises(ValueError, match="bad hash"):
        function({})


def test_callable_keeps_allocation_alive_and_releases_it():
    compiler = X86Compiler("native_lifetime")
    result = compiler.call(str, compiler.data)
    owner = compiler.finish(result)
    allocation = owner.memory.mapping
    memory_ref = weakref.ref(owner.memory)
    function = owner.make_callable()
    del owner, compiler
    gc.collect()
    assert memory_ref() is not None
    assert function(123) == "123"
    assert not allocation.closed

    del function
    gc.collect()
    assert memory_ref() is None
    # Keeping the mmap itself alive is intentional here: no owner or builtin
    # holds it anymore, so it can now be closed without dangling function code.
    allocation.close()


def test_method_metadata_survives_gc_clearing_its_ctypes_storage():
    compiler = X86Compiler("method_metadata")
    function = compiler.finish(compiler.call(str, compiler.data)).make_callable()
    method = function.__self__.method
    if isinstance(method, ctypes.Structure):
        # GC can clear reachable storage inside an unreachable callable cycle
        # before dropping the builtin's last reference. Simulate that ordering.
        get_slot = ctypes.pythonapi.PyType_GetSlot
        get_slot.argtypes = (ctypes.py_object, ctypes.c_int)
        get_slot.restype = ctypes.c_void_p
        clear = ctypes.PYFUNCTYPE(ctypes.c_int, ctypes.py_object)(get_slot(type(method), 51))  # Py_tp_clear
        assert clear(method) == 0
    get_flags = ctypes.pythonapi.PyCFunction_GetFlags
    get_flags.argtypes = (ctypes.py_object,)
    get_flags.restype = ctypes.c_int
    assert get_flags(function) == 0x0080 | 0x0002  # METH_FASTCALL | METH_KEYWORDS


def test_cyclic_callables_keep_method_metadata_alive_until_deallocation():
    memory_references = []
    callbacks = []
    enabled = gc.isenabled()
    gc.disable()
    try:
        for index in range(256):
            compiler = X86Compiler(f"cyclic_callback_{index}")
            function = compiler.finish(compiler.call(str, compiler.data)).make_callable()
            assert function(index) == str(index)
            function.__module__ = {"callback": function}
            callbacks.append(function)
            memory_references.append(weakref.ref(function.__self__.memory))
        del compiler, function
        callbacks.clear()
        gc.collect()
        assert all(reference() is None for reference in memory_references)
    finally:
        if enabled:
            gc.enable()

def test_recursive_callable_cycle_releases_allocation():
    holder = []
    compiler = X86Compiler("native_cycle")
    compiler.constant(holder)
    result = compiler.call(str, compiler.data)
    owner = compiler.finish(result)
    memory_ref = weakref.ref(owner.memory)
    function = owner.make_callable()
    holder.append(function)
    del compiler, owner, function, holder
    gc.collect()
    assert memory_ref() is None


def test_executable_mapping_is_not_writable():
    compiler = X86Compiler("native_permissions")
    result = compiler.call(str, compiler.data)
    owner = compiler.finish(result)
    address = owner.memory.address
    for line in Path("/proc/self/maps").read_text().splitlines():
        region, permissions, *_ = line.split()
        start, end = (int(part, 16) for part in region.split("-"))
        if start <= address < end:
            assert permissions.startswith("r-x")
            break
    else:
        pytest.fail("Generated code mapping was not found")


def test_borrowed_slots_cannot_be_returned_or_released():
    compiler = X86Compiler("native_borrowed")
    with pytest.raises(ValueError, match="owned reference"):
        compiler.finish(compiler.data)
    with pytest.raises(ValueError, match="borrowed"):
        compiler.release(compiler.data)


@pytest.mark.parametrize("gap", [0, 120, 121, 122, 127, 128, 256])
def test_assembler_forward_branches_select_the_correct_path_at_short_jump_boundaries(gap):
    asm = X86Assembler()
    asm.emit(b"\x85\xff", "test edi, edi")
    asm.mov_imm(11, 0)  # MOV must preserve the comparison flags.
    asm.jump("taken", "z")
    asm.mov_imm(0, 2)
    asm.emit(b"\xc3" + b"\x90" * gap, "ret; padding")
    asm.label("taken")
    asm.mov_imm(0, 1)
    asm.emit(b"\xc3", "ret")
    code = asm.finish()
    assert asm.finish() == code
    memory = ExecutableMemory(code)
    function = ctypes.PYFUNCTYPE(ctypes.c_uint64, ctypes.c_int)(memory.address)
    assert function(0) == 1
    assert function(1) == 2


@pytest.mark.parametrize("gap", [0, 120, 121, 122, 127, 128, 256])
def test_assembler_backward_branches_preserve_loops_at_short_jump_boundaries(gap):
    asm = X86Assembler()
    asm.mov_imm(0, 0)
    asm.label("loop")
    asm.emit(b"\xff\xc0" + b"\x90" * gap + b"\x39\xf8", "inc eax; padding; cmp eax, edi")
    asm.jump("loop", "nz")
    asm.emit(b"\xc3", "ret")
    memory = ExecutableMemory(asm.finish())
    function = ctypes.PYFUNCTYPE(ctypes.c_uint64, ctypes.c_int)(memory.address)
    assert function(4) == 4


def test_assembler_relaxes_interdependent_branches_after_composing_fragments():
    head = X86Assembler()
    head.emit(b"\x85\xff", "test edi, edi")
    head.jump("done", "z")
    tail = X86Assembler()
    tail.jump("done", "z")
    tail.emit(b"\x90" * 124, "padding")
    tail.label("done")
    tail.mov_imm(0, 42)
    tail.emit(b"\xc3", "ret")
    head.extend(tail)
    original_size = len(head.code)
    code = head.finish()
    # The second branch shrinking makes the first fit a signed byte.
    assert len(code) == original_size - 8
    memory = ExecutableMemory(code)
    function = ctypes.PYFUNCTYPE(ctypes.c_uint64, ctypes.c_int)(memory.address)
    assert function(0) == 42
    assert function(1) == 42


@pytest.mark.parametrize("register", [0, 1, 2, 6, 7, 8, 9, 10, 11])
@pytest.mark.parametrize("value", [0, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x100000000, 0xFFFFFFFFFFFFFFFF])
def test_assembler_immediate_loads_preserve_all_bits_and_clear_upper_register_bits(register, value):
    asm = X86Assembler()
    asm.mov_imm(register, 0xFEDCBA9876543210)
    asm.mov_imm(register, value)
    rex = 0x48 | ((register >> 3) << 2)
    asm.emit(bytes([rex, 0x89, 0xC0 | ((register & 7) << 3)]), "mov rax, tested_register")
    asm.emit(b"\xc3", "ret")
    memory = ExecutableMemory(asm.finish())
    function = ctypes.PYFUNCTYPE(ctypes.c_uint64)(memory.address)
    assert function() == value


def test_native_stack_size_is_bounded():
    compiler = X86Compiler("native_large")
    for _ in range(8192):
        compiler.slot()
    result = compiler.call(str, compiler.data)
    with pytest.raises(ValueError, match="64 KiB"):
        compiler.finish(result)


def test_native_function_can_be_reentered():
    def recurse(depth):
        return function(depth - 1) + 1 if depth else 0

    compiler = X86Compiler("native_reentrant")
    result = compiler.call(recurse, compiler.data)
    function = compiler.finish(result).make_callable()
    assert function(25) == 25


def test_direct_native_calls_restore_recursion_state_after_failure():
    def recurse(depth):
        return function(depth - 1) + 1 if depth else 0

    compiler = X86Compiler("native_inner")
    inner = compiler.finish(compiler.call(recurse, compiler.data)).make_callable()
    compiler = X86Compiler("native_outer")
    function = compiler.finish(compiler.call(inner, compiler.data)).make_callable()
    del inner
    previous = sys.gettrace()
    try:
        with pytest.raises(RecursionError):
            function(sys.getrecursionlimit() * 2)
    finally:
        # A recursion error inside a Python trace hook disables tracing.
        if sys.gettrace() is not previous:
            sys.settrace(previous)
    for _ in range(20):
        assert function(10) == 10


def test_positive_recursion_guard_status_skips_native_callee(monkeypatch):
    # Py_EnterRecursiveCall normalizes an error to positive 1. Use a native
    # stub to exercise that contract without approaching the C stack limit.
    message = ctypes.create_string_buffer(b"native recursion guard")
    api = ctypes.cast(ctypes.pythonapi.PyErr_SetString, ctypes.c_void_p).value
    assert api is not None
    asm = X86Assembler()
    asm.emit(b"\x55\x48\x89\xe5", "push rbp; mov rbp, rsp")
    asm.mov_imm(7, id(RecursionError))
    asm.mov_imm(6, ctypes.addressof(message))
    asm.mov_imm(11, api)
    asm.emit(b"\x31\xc0\x41\xff\xd3", "xor eax, eax; call r11")
    asm.emit(b"\xb8\x01\x00\x00\x00\xc9\xc3", "mov eax, 1; leave; ret")
    memory = ExecutableMemory(asm.finish())
    stub = ctypes.PYFUNCTYPE(ctypes.c_int, ctypes.c_void_p)(memory.address)
    stub.memory = memory
    stub.message = message
    seen = []

    def convert(value):
        seen.append(value)
        return value

    compiler = X86Compiler("native_guard_inner")
    inner = compiler.finish(compiler.call(convert, compiler.data)).make_callable()
    monkeypatch.setattr(ctypes.pythonapi, "Py_EnterRecursiveCall", stub)
    compiler = X86Compiler("native_guard_outer")
    function = compiler.finish(compiler.call(inner, compiler.data)).make_callable()
    with pytest.raises(RecursionError, match="native recursion guard"):
        function(42)
    assert seen == []


@pytest.mark.parametrize("mutation", ["clear", "value", "keys"])
def test_dictionary_template_mutation_falls_back_without_losing_values(mutation):
    compiler = X86Compiler("native_template")
    values = {name: compiler.copy_reference(compiler.data) for name in ("first", "second")}
    owner = compiler.finish(compiler.make_dict(values, consume=True))
    function = owner.make_callable()
    value = object()
    expected = {"first": value, "second": value}
    assert function(value) == expected
    template = next((item.data for item in owner.constants if isinstance(item, DictionaryTemplate)), None)
    if template is not None:
        if mutation == "clear":
            template.clear()
        elif mutation == "value":
            template["first"] = []
        else:
            del template["first"]
            template["other"] = None
    references = sys.getrefcount(value)
    for _ in range(100):
        assert function(value) == expected
    gc.collect()
    assert sys.getrefcount(value) == references


@pytest.mark.parametrize("consume", [False, True])
@pytest.mark.parametrize("count", [2, 4, 29, 30, 31])
def test_output_dictionary_mutations_and_reference_lifetime(consume, count):
    names = tuple(f"field_{index}" for index in range(count))
    compiler = X86Compiler("native_dict_operations")
    values = {name: compiler.copy_reference(compiler.data) for name in names}
    function = compiler.finish(compiler.make_dict(values, consume=consume)).make_callable()
    value = object()
    references = sys.getrefcount(value)
    for _ in range(20):
        result = function(value)
        other = function(value)
        assert type(result) is dict
        assert list(result) == list(names)
        assert list(reversed(result)) == list(reversed(names))
        assert result.copy() == dict.fromkeys(names, value)
        assert result.pop(names[0]) is value
        result[names[0]] = value
        assert result.popitem() == (names[0], value)
        result.update(dict.fromkeys((f"extra_{index}" for index in range(35)), None))
        result[42] = value
        del result[names[-1]]
        assert other == dict.fromkeys(names, value)
        result.clear()
        result["after_clear"] = value
        assert result == {"after_clear": value}
        del result, other
    gc.collect()
    assert sys.getrefcount(value) == references


def test_output_dictionary_accepts_arbitrary_string_keys():
    names = ("__class__", "__dict__", "", "not an identifier", "ключ")
    compiler = X86Compiler("native_arbitrary_dict_keys")
    values = {name: compiler.copy_reference(compiler.data) for name in names}
    function = compiler.finish(compiler.make_dict(values, consume=True)).make_callable()
    value = object()
    assert function(value) == dict.fromkeys(names, value)


def test_output_dictionary_keeps_shared_keys_alive_after_the_function_is_collected():
    compiler = X86Compiler("native_dict_outlives_code")
    values = {name: compiler.copy_reference(compiler.data) for name in ("first", "second")}
    owner = compiler.finish(compiler.make_dict(values, consume=True))
    reference = weakref.ref(owner.memory)
    function = owner.make_callable()
    value = object()
    result = function(value)
    del owner, compiler, function
    gc.collect()
    assert reference() is None
    assert result == {"first": value, "second": value}
    result.update({f"field_{index}": index for index in range(35)})
    assert result["first"] is value
    result.clear()
    assert result == {}


@pytest.mark.skipif(sys.version_info[:2] not in {(3, 14), (3, 15)}, reason="Shared dictionary allocator requires CPython 3.14/3.15")
def test_dictionary_template_retains_its_original_type_after_carrier_class_changes():
    compiler = X86Compiler("native_dict_carrier_changed")
    values = {name: compiler.copy_reference(compiler.data) for name in ("first", "second")}
    owner = compiler.finish(compiler.make_dict(values, consume=True))
    template = next((item for item in owner.constants if isinstance(item, DictionaryTemplate)), None)
    if template is None or template.kind != 2:
        pytest.skip("Shared-key storage is unsupported")
    original = weakref.ref(template.keys_owner)
    replacement = type("ReplacementCarrier", (), {})
    template.owner.__class__ = replacement
    template.data.clear()
    gc.collect()
    assert original() is not None
    function = owner.make_callable()
    value = object()
    for _ in range(20):
        assert function(value) == {"first": value, "second": value}
    del compiler, owner, template, function
    gc.collect()
    assert original() is None


@pytest.mark.skipif(sys.version_info[:2] not in {(3, 14), (3, 15)}, reason="Shared dictionary allocator requires CPython 3.14/3.15")
def test_dictionary_value_allocation_failure_releases_all_references(monkeypatch):
    memory = ExecutableMemory(b"\xf3\x0f\x1e\xfa\x31\xc0\xc3")  # endbr64; xor eax, eax; ret
    stub = ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.c_size_t)(memory.address)
    monkeypatch.setattr(ctypes.pythonapi, "PyMem_Malloc", stub)
    compiler = X86Compiler("native_dict_no_memory")
    values = {name: compiler.copy_reference(compiler.data) for name in ("first", "second")}
    owner = compiler.finish(compiler.make_dict(values, consume=True))
    if not any(isinstance(item, DictionaryTemplate) and item.kind == 2 for item in owner.constants):
        pytest.skip("Shared-key storage is unsupported")
    function = owner.make_callable()
    value = object()
    references = sys.getrefcount(value)
    for _ in range(20):
        with pytest.raises(MemoryError):
            function(value)
    gc.collect()
    assert sys.getrefcount(value) == references


def test_function_context_uses_the_calling_thread_for_all_entry_protocols():
    api = ctypes.cast(ctypes.pythonapi.PyThreadState_Get, ctypes.c_void_p).value
    assert api is not None
    get_state = ctypes.PYFUNCTYPE(ctypes.c_void_p)(api)
    compiler = X86Compiler("native_context")
    context = compiler.function_context("PyThreadState_Get")
    assert compiler.function_context("PyThreadState_Get") == context
    function = compiler.finish(compiler.call_c("PyLong_FromVoidPtr", context)).make_callable()
    compiler = X86Compiler("native_context_outer")
    outer = compiler.finish(compiler.call(function, compiler.data)).make_callable()
    barrier = Barrier(4)

    def exercise(value):
        barrier.wait(timeout=10)
        state = get_state()
        for _ in range(20):
            assert function(value) == state
            assert function(data=value) == state
            assert function(**{bytearray(b"data").decode(): value}) == state
            assert outer(value) == state
        return state

    with ThreadPoolExecutor(max_workers=4) as executor:
        states = list(executor.map(exercise, range(4)))
    assert len(set(states)) == 4


def test_attribute_batch_releases_earlier_fields_when_a_later_field_is_missing():
    class Model:
        pass

    compiler = X86Compiler("native_partial_attributes")
    first, second = compiler.get_attrs(compiler.data, ("first", "second"))
    function = compiler.finish(compiler.make_dict({"first": first, "second": second}, consume=True)).make_callable()
    value = object()
    model = Model()
    model.first, model.second = value, value
    for _ in range(20):
        assert function(model) == {"first": value, "second": value}
    references = reference_counts([value])[0]
    del model.second
    for _ in range(20):
        with pytest.raises(AttributeError):
            function(model)
    assert reference_counts([value])[0] == references - 1
    model.second = value
    assert function(model) == {"first": value, "second": value}


def test_dictionary_transfer_tracks_gc_values():
    class Value:
        pass

    compiler = X86Compiler("native_gc_dict")
    values = {name: compiler.copy_reference(compiler.data) for name in ("first", "second")}
    function = compiler.finish(compiler.make_dict(values, consume=True)).make_callable()
    value = Value()
    reference = weakref.ref(value)
    result = function(value)
    assert gc.is_tracked(result)
    value.result = result
    del result, value
    gc.collect()
    assert reference() is None


def test_vectorcall_keyword_only_arguments():
    def constructor(a, /, b, *, c):
        return a, b, c

    compiler = X86Compiler("native_keywords")
    result = compiler.vectorcall(
        constructor, (compiler.data, compiler.constant(2), compiler.constant(3)), ("c",),
    )
    function = compiler.finish(result).make_callable()
    assert function(1) == (1, 2, 3)


def test_lazy_state_is_initialized_once_and_only_on_failure():
    allocations = []

    class State:
        def __init__(self):
            self.errors = 0
            allocations.append(weakref.ref(self))

    def convert(value):
        if value < 0:
            raise ValueError("negative")
        return value

    def recover(state, error):
        assert isinstance(error, ValueError)
        state.errors += 1
        return state.errors

    compiler = X86Compiler("native_lazy")
    state = compiler.lazy_call(State)
    first = compiler.guarded_call(convert, (compiler.data,), recover, state)
    second = compiler.guarded_call(convert, (compiler.data,), recover, state)
    result = compiler.call(lambda a, b: (a, b), first, second)
    function = compiler.finish(result).make_callable()
    assert function(3) == (3, 3)
    assert allocations == []
    assert function(-1) == (1, 2)
    assert len(allocations) == 1
    gc.collect()
    assert allocations[0]() is None


@pytest.mark.parametrize("failure", ["factory", "handler"])
def test_failed_cold_handler_releases_local_and_global_references(failure):
    allocations = []

    class State:
        def __init__(self):
            allocations.append(weakref.ref(self))
            if failure == "factory":
                raise RuntimeError("factory failed")

    def convert(value):
        raise ValueError("original failure")

    def recover(state, error):
        raise RuntimeError("handler failed")

    compiler = X86Compiler("native_recovery_failure")
    copied = compiler.call(lambda x: x, compiler.data)
    state = compiler.lazy_call(State)
    result = compiler.guarded_call(convert, (copied,), recover, state)
    function = compiler.finish(result).make_callable()
    value = object()
    references = reference_counts([value])
    for _ in range(100):
        with pytest.raises(RuntimeError, match=f"{failure} failed"):
            function(value)
    assert reference_counts([value]) == references
    assert all(reference() is None for reference in allocations)


@pytest.mark.parametrize("fallback", [False, True])
def test_dictionary_arrays_preserve_keys_values_and_ownership(fallback):
    compiler = X86Compiler("native_dictionary")
    if fallback:
        compiler.dict_from_items = False
    value = compiler.call(lambda x: x, compiler.data)
    result = compiler.make_dict({"first": value, "second": value, 3: value})
    function = compiler.finish(result).make_callable()
    data = object()
    references = sys.getrefcount(data)
    for _ in range(100):
        assert function(data) == {"first": data, "second": data, 3: data}
    assert sys.getrefcount(data) == references


@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("value", [object(), None, True, 42, sys.intern("native_refcount")])
def test_reference_operations_handle_mortal_and_immortal_objects(fallback, value):
    compiler = X86Compiler("native_reference")
    if fallback:
        compiler.refcount_mode = None
    copied = compiler.new_reference(value)
    result = compiler.call(lambda x: x, copied)
    function = compiler.finish(result).make_callable()
    for _ in range(3):
        assert function(None) is value
    # Retaining a small integer's reference count as an int can itself add
    # a reference to that integer when the count happens to equal its value.
    references = float(sys.getrefcount(value))
    for _ in range(100):
        function(None)
    after = float(sys.getrefcount(value))
    assert after == references


@pytest.mark.parametrize("fallback", [False, True])
def test_last_reference_runs_destructor(fallback):
    destroyed = []

    class Value:
        def __del__(self):
            destroyed.append(True)

    compiler = X86Compiler("native_destructor")
    if fallback:
        compiler.refcount_mode = None
    temporary = compiler.call(Value)
    compiler.release(temporary)
    result = compiler.new_reference(None)
    function = compiler.finish(result).make_callable()
    assert function(None) is None
    assert destroyed == [True]


@pytest.mark.parametrize("mode", ["inline", "c_api", "no_dealloc"])
@pytest.mark.parametrize("failure", [False, True])
def test_last_reference_cleanup_allows_destructor_reentry(mode, failure):
    seen = []
    functions = []

    class Value:
        def __del__(self):
            seen.append(functions[0](None))

    def create(data):
        return Value() if data else None

    def finish(data):
        if data and failure:
            raise ValueError("original exception")

    compiler = X86Compiler("native_destructor_reentry")
    if mode == "c_api":
        compiler.refcount_mode = None
    elif mode == "no_dealloc":
        compiler.dealloc_address = None
    temporary = compiler.call(create, compiler.data)
    result = compiler.call(finish, compiler.data)
    compiler.release(temporary)
    functions.append(compiler.finish(result).make_callable())
    for _ in range(30):
        if failure:
            with pytest.raises(ValueError, match="original exception"):
                functions[0](1)
        else:
            assert functions[0](1) is None
    assert seen == [None] * 30


def test_cleanup_preserves_references_across_branch_merge():
    compiler = X86Compiler("native_branch_cleanup")
    value = compiler.call(lambda data: data["value"], compiler.data)
    release = compiler.call(lambda data: data["release"], compiler.data)
    done = compiler.label("merge")
    compiler.branch_if(release, constant=False, label=done)
    compiler.release(value)
    compiler.asm.label(done)
    result = compiler.new_reference(None)
    function = compiler.finish(result).make_callable()
    data = object()
    cases = [{"value": data, "release": False}, {"value": data, "release": True}]
    references = sys.getrefcount(data)
    for case in cases * 100:
        function(case)
    assert sys.getrefcount(data) == references


@pytest.mark.parametrize("seed", range(12))
def test_null_analysis_matches_all_reachable_paths(seed):
    randomizer = random.Random(seed)  # noqa: S311
    slots = tuple(Slot(index) for index in range(4))
    initial = frozenset(slots[:2])
    assembler = X86Assembler()
    for index in range(6):
        assembler.flow.append(("label", f"block_{index}"))
        for _ in range(3):
            assembler.flow.append((randomizer.choice(("write", "clear")), randomizer.choice(slots)))
        assembler.flow.append((randomizer.choice(("jump", "branch")),
                               randomizer.choice(("error", *(f"block_{i}" for i in range(6))))))
    assembler.flow.append(("label", "done"))
    labels = {operand: index for index, (kind, operand) in enumerate(assembler.flow) if kind == "label"}
    pending, visited = [(0, initial)], set()
    while pending:
        index, state = pending.pop()
        if (index, state) in visited:
            continue
        visited.add((index, state))
        kind, operand = assembler.flow[index]
        if kind == "write":
            state -= {operand}
        elif kind == "clear":
            state |= {operand}
        if kind in {"jump", "branch"} and operand in labels:
            pending.append((labels[operand], state))
        if kind != "jump" and index + 1 < len(assembler.flow):
            pending.append((index + 1, state))
    for label, position in labels.items():
        states = [state for index, state in visited if index == position]
        expected = frozenset.intersection(*states) if states else frozenset()
        assert assembler.definitely_null_at(label, list(initial)) == expected


def test_cleanup_handles_native_loops():
    class Value:
        pass

    compiler = X86Compiler("native_loop_cleanup")
    loop, done = compiler.label("loop"), compiler.label("done")
    compiler.asm.label(loop)
    value = compiler.call(lambda data: data.pop() if data else None, compiler.data)
    compiler.branch_if(value, None, done)
    compiler.release(value)
    compiler.asm.jump(loop)
    compiler.asm.label(done)
    result = compiler.new_reference(None)
    function = compiler.finish(result).make_callable()
    values = [Value() for _ in range(10)]
    references = [weakref.ref(item) for item in values]
    assert function(values) is None
    assert values == []
    assert all(reference() is None for reference in references)


def test_cleanup_observes_owned_references_written_by_c_api():
    if not hasattr(ctypes.pythonapi, "PyDict_GetItemRef"):
        pytest.skip("PyDict_GetItemRef is not exported by this interpreter")
    compiler = X86Compiler("native_output_reference")
    value = compiler.slot(owned=True)
    compiler.call_c("PyDict_GetItemRef", compiler.data, compiler.constant("value"), Address(value), result="int")
    result = compiler.new_reference(None)
    function = compiler.finish(result).make_callable()
    data = {"value": object()}
    references = sys.getrefcount(data["value"])
    for _ in range(100):
        function(data)
    after = sys.getrefcount(data["value"])
    assert after == references


@pytest.mark.parametrize("fallback", [False, True])
def test_retained_release_keeps_values_alive_until_their_container_is_destroyed(fallback):
    destroyed = []

    class Value:
        def __del__(self):
            destroyed.append(True)

    compiler = X86Compiler("native_retained_reference")
    if fallback:
        compiler.refcount_mode = None
    value = compiler.call(Value)
    result = compiler.make_dict({"value": value})
    compiler.release(value, nonnull=True, retained=True)
    function = compiler.finish(result).make_callable()
    for index in range(100):
        result = function(None)
        assert len(destroyed) == index
        del result
        assert len(destroyed) == index + 1


@pytest.mark.parametrize("shared", [False, True])
def test_list_to_tuple_transfer_preserves_ownership_and_shared_lists(shared):
    value = object()
    source = [value, value]
    compiler = X86Compiler("native_tuple_transfer")
    if shared:
        temporary = compiler.new_reference(source)
    else:
        temporary = compiler.call_c("PyList_New", Immediate(0))
        for _ in range(2):
            item = compiler.new_reference(value)
            compiler.call_c("PyList_Append", temporary, item, result="int")
            compiler.release(item)
    result = compiler.list_as_tuple(temporary)
    compiler.release(temporary)
    function = compiler.finish(result).make_callable()
    references = sys.getrefcount(value)
    for _ in range(100):
        converted = function(None)
        assert converted == (value, value)
        assert source == [value, value]
        del converted
    gc.collect()
    assert sys.getrefcount(value) == references


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("mode", ["inline", "direct", "limited", "budget"])
def test_nested_native_loop_preserves_callee_saved_registers(monkeypatch, failure, mode):
    if mode == "limited":
        monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.MAX_INLINE_CODE_SIZE", 0)
    inner = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(list[list[int]])
    compiler = X86Compiler("native_preserved_loop_registers")
    assert compiler.reserve_loop_registers()
    seeds = (0xFEDCBA0987654321, 0x0123456789ABCDEF, 0x9988776655443322, 0x8899AABBCCDDEEFF)
    for register, seed in zip((12, 13, 14, 15), seeds, strict=True):
        compiler.asm.mov_imm(register, seed)
    if mode != "direct":
        result = compiler.inline_call(
            inner, compiler.data, (lambda error: ["failed"]) if failure else None,
            code_budget=0 if mode == "budget" else None,
        )
    else:
        result = (
            compiler.guarded_call(inner, (compiler.data,), lambda error: ["failed"])
            if failure else compiler.call_native(inner, compiler.data, "error")
        )
    invalid, done = compiler.label("invalid_register"), compiler.label("registers_preserved")
    for register, seed in zip((12, 13, 14, 15), seeds, strict=True):
        compiler.asm.mov_imm(11, seed)
        compiler.asm.emit(bytes([0x4D, 0x39, 0xD8 | (register & 7)]), "check preserved loop register")
        compiler.asm.jump(invalid, "nz")
    compiler.asm.jump(done)
    compiler.asm.label(invalid)
    message = ctypes.create_string_buffer(b"Native loop clobbered a callee-saved register")
    compiler.constants.append(message)
    compiler.call_c("PyErr_SetString", compiler.constant(AssertionError), Immediate(ctypes.addressof(message)),
                    result="void")
    compiler.asm.jump("error")
    compiler.asm.label(done)
    compiler.release_loop_registers()
    function = compiler.finish(result).make_callable()
    for _ in range(100):
        if failure:
            assert function([[1000], [2000, "invalid"]]) == ["failed"]
            assert function(iter([[1000], [2000, "invalid"]])) == ["failed"]
        else:
            assert function([[1000], [2000, 3000]]) == [[1000], [2000, 3000]]
            assert function(iter([[1000], [2000, 3000]])) == [[1000], [2000, 3000]]


def test_reference_replacement_publishes_result_before_destructor_reentry():
    functions, destroyed = [], []

    class Value:
        def __del__(self):
            destroyed.append(functions[0](0))

    compiler = X86Compiler("native_replace_reference")
    previous = compiler.call(lambda data: Value() if data else None, compiler.data)
    replacement = compiler.call(lambda: ["replacement"])
    compiler.replace_reference(replacement, previous)
    functions.append(compiler.finish(previous).make_callable())
    for _ in range(100):
        assert functions[0](1) == ["replacement"]
    assert destroyed == [["replacement"]] * 100


@pytest.mark.parametrize("reserved", [0, 1, 2, 5])
def test_private_tuple_builder_grows_shrinks_and_tracks_final_cycles(reserved):
    references = []

    class Value:
        pass

    def create():
        gc.collect()
        for candidate in gc.get_objects():
            if type(candidate) is tuple:
                list(candidate)
        value = Value()
        references.append(weakref.ref(value))
        return value

    compiler = X86Compiler("native_private_tuple_builder")
    result, written = reserve_iterator_output(compiler, Immediate(reserved), direct_tuple=True)
    for _ in range(3):
        value = compiler.call(create)
        append_tuple_item(compiler, result, value, written)
    finish_tuple_output(compiler, result, written)
    function = compiler.finish(result).make_callable()
    for _ in range(10):
        result = function(None)
        assert len(result) == 3
        assert gc.is_tracked(result)
        for value in result:
            value.cycle = result
        del value, result
        gc.collect()
        assert all(reference() is None for reference in references)
