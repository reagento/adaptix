import ctypes
import struct
import sys
from dataclasses import dataclass
from functools import cache, partial

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.code_tools.native_dictionary import guard_dictionary_value
from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.native.plan import IterablePlan
from adaptix._internal.morphing.native.runtime import ErrorState, check_list_input, finish_iterable, handle_error
from adaptix._internal.special_cases_optimization import as_is_stub

LAYOUT = get_cpython_layout()

MISSING = object()


@cache
def list_layout_supported():
    if LAYOUT is None:
        return False
    probe = [object(), object()]
    if (
        ctypes.c_ssize_t.from_address(id(probe) + LAYOUT.var_size).value != len(probe)
        or ctypes.c_ssize_t.from_address(id(probe) + LAYOUT.list_allocated).value < 2  # noqa: PLR2004
    ):
        return False
    items = ctypes.c_void_p.from_address(id(probe) + LAYOUT.list_items).value
    return bool(items and ctypes.c_void_p.from_address(items).value == id(probe[0]))


@cache
def tuple_item_offset():
    if LAYOUT is None:
        return None
    offset = LAYOUT.tuple_items
    probe = (object(), object())
    return offset if ctypes.c_void_p.from_address(id(probe) + offset).value == id(probe[0]) else None


class SequenceSubclassCache(ctypes.Structure):
    _fields_ = [("cls", ctypes.c_void_p), ("version", ctypes.c_uint32), ("enabled", ctypes.c_uint32)]

    def __init__(self, expected):
        super().__init__()
        self.expected = expected
        self.held_class = None

    def learn(self, data):
        from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
            GET_SLOT,
            IS_SUBTYPE,
            LOOKUP,
            get_type_version,
        )

        cls = type(data)
        enabled = (
            type(cls) is type and IS_SUBTYPE(cls, self.expected)
            and LOOKUP(cls, "__iter__") is self.expected.__iter__
            and GET_SLOT(cls, 62) == GET_SLOT(self.expected, 62)
        )
        self.enabled = 0
        self.held_class = cls
        self.cls = id(cls)
        self.version = get_type_version(cls)
        self.enabled = enabled


def check_sequence_type(c, input_type, generic):
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        c.branch_if_type(c.data, input_type, generic, invert=True)
        return
    accepted, guard, learn = (
        c.label(prefix) for prefix in ("sequence_type_ok", "sequence_subclass_guard", "sequence_subclass_learn")
    )
    c.branch_if_type(c.data, input_type, accepted)
    cache = SequenceSubclassCache(input_type)
    c.constants.append(cache)
    c.asm.label(guard)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.object_type]), "load sequence subclass")
    c.asm.mov_imm(11, ctypes.addressof(cache))
    c.check_cached_type(learn)
    c.asm.emit(b"\x41\x83\x7b\x0c\x00", "check unchanged sequence iterator")
    c.asm.jump(generic, "z")
    c.asm.jump(accepted)
    c.asm.label(learn)
    c.release(c.call(cache.learn, c.data))
    c.asm.jump(guard)
    c.asm.label(accepted)


def check_sequence_mapping(c, input_type):
    from adaptix._internal.morphing import iterable_provider  # noqa: PLC0415

    exact, done = c.label("exact_sequence_mapping"), c.label("sequence_mapping_checked")
    c.branch_if_type(c.data, input_type, exact)
    c.release(c.call(check_list_input, c.data))
    c.asm.jump(done)
    c.asm.label(exact)
    check_list_mapping(c, input_type=input_type, module=iterable_provider, attribute="CollectionsMapping")
    c.asm.label(done)


def load_sequence_items(c, register, source, sequence_type):
    prefix = 0x48 | ((register >> 3) << 2) | (source >> 3)
    operand = 0x40 | ((register & 7) << 3) | (source & 7)
    opcode, offset = (0x8B, c.layout.list_items) if sequence_type is list else (0x8D, tuple_item_offset())
    c.asm.emit(bytes([prefix, opcode, operand, offset]), "load sequence items pointer")










def check_list_mapping(c, *, input_type=list, check=check_list_input, module=None, attribute="Mapping"):
    """Use the ABC's negative cache while its class and registry remain valid."""
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        c.release(c.call(check, c.data))
        return
    import _abc as abc_accelerator  # noqa: PLC0415
    import collections.abc  # noqa: PLC0415

    from adaptix._internal.code_tools.native_access import LOOKUP, get_type_version, pointer, size  # noqa: PLC0415

    module = collections.abc if module is None else module
    mapping = getattr(module, attribute)
    if type(mapping) is not type(collections.abc.Iterable) or issubclass(input_type, mapping):
        c.release(c.call(check, c.data))
        return
    get_state = ctypes.pythonapi.PyModule_GetState
    get_state.argtypes, get_state.restype = (ctypes.py_object,), ctypes.c_void_p
    state = get_state(abc_accelerator)
    implementation = mapping._abc_impl
    token = abc_accelerator.get_cache_token()
    if (
        not state
        or pointer(state) != id(type(implementation))
        or size(state + c.layout.abc_invalidation_counter) != token
    ):
        c.release(c.call(check, c.data))
        return
    negative = ctypes.cast(pointer(id(implementation) + c.layout.abc_negative_cache), ctypes.py_object).value
    key = next((reference for reference in negative if reference() is input_type), None)
    if key is None:
        c.release(c.call(check, c.data))
        return
    mask, table = size(id(negative) + c.layout.set_mask), pointer(id(negative) + c.layout.set_table)
    indices = [index for index in range(mask + 1) if pointer(table + index * c.layout.set_entry_size) == id(key)]
    if not indices:
        c.release(c.call(check, c.data))
        return
    LOOKUP(mapping, "__subclasshook__")
    LOOKUP(type(mapping), "__instancecheck__")
    generic, done = c.label("mapping_check_slow"), c.label("not_a_mapping")
    guard_dictionary_value(c, vars(module), attribute, mapping, None, generic)
    for cls in (mapping, type(mapping)):
        c.load(0, c.constant(cls))
        c.asm.emit(
            b"\x81\xb8" + struct.pack("<iI", c.layout.type_version, get_type_version(cls)), "cmp Mapping class version",
        )
        c.asm.jump(generic, "nz")
    c.constants.extend((abc_accelerator, implementation, negative, key))
    c.asm.mov_imm(11, state)
    c.asm.mov_imm(0, token)
    c.asm.emit(
        b"\x49\x3b\x43" + bytes([c.layout.abc_invalidation_counter]), "cmp rax, [r11+8]  # ABC invalidation counter",
    )
    c.asm.jump(generic, "nz")
    c.load(0, c.constant(negative))
    index = indices[0]
    c.asm.emit(
        b"\x48\x81\x78" + bytes([c.layout.set_mask]) + struct.pack("<i", index), "cmp negative cache mask, entry index",
    )
    c.asm.jump(generic, "b")
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.set_table]), "mov rax, [rax+40]  # negative cache table")
    c.load(11, c.constant(key))
    c.asm.emit(
        b"\x4c\x39\x98" + struct.pack("<i", index * c.layout.set_entry_size), "cmp cached weak reference to list",
    )
    c.asm.jump(generic, "nz")
    c.asm.jump(done)
    c.asm.label(generic)
    c.release(c.call(check, c.data))
    c.asm.label(done)


@dataclass(frozen=True)
class ListProgram(IterablePlan):
    def emit(self, c):
        from adaptix._internal.morphing.native.registry import identity_spec  # noqa: PLC0415
        from adaptix._internal.morphing.native.x86_64.scalar import ScalarProgram, get_program  # noqa: PLC0415

        spec = identity_spec(self.mapper)
        program = get_program(self.mapper)
        if isinstance(program, ScalarProgram) and program.coerce_int:
            spec = program.types, program.nullable
        tuple_input, done = c.label("sequence_tuple_input"), c.label("sequence_done")
        result = c.slot(owned=True)
        sequence_input, set_input = c.label("sequence_input"), c.label("sequence_set_input")
        for cls in (set, frozenset):
            c.branch_if_type(c.data, cls, set_input)
        c.asm.jump(sequence_input)
        c.asm.label(set_input)
        value = map_iterator(c, **vars(self), output_type=self.origin if self.loading else self.dump_as)
        c.transfer(value, result)
        c.asm.jump(done)
        c.asm.label(sequence_input)
        c.branch_if_type(c.data, tuple, tuple_input)
        for input_type in (list, tuple):
            if input_type is tuple:
                c.asm.label(tuple_input)
            output_type = self.origin if self.loading else self.dump_as
            if spec is not None:
                value = copy_scalar_list(
                    c, spec, self.fallback, loading=self.loading, strict_coercion=self.strict_coercion,
                    input_type=input_type, output_type=output_type,
                    slow_mapper=self if isinstance(program, ScalarProgram) and program.coerce_int else None,
                )
            else:
                value = map_list(c, **vars(self), input_type=input_type, output_type=output_type)
            c.transfer(value, result)
            if input_type is list:
                c.asm.jump(done)
        c.asm.label(done)
        return result


def build_list_program(plan: IterablePlan, c):
    if not c.has_validated_object_header or not list_layout_supported() or tuple_item_offset() is None:
        return None
    return ListProgram(**vars(plan))


def map_list(  # noqa: PLR0915
    c, *, origin, mapper, fallback, debug_trail, loading, strict_coercion,
    input_type=list, output_type=list,
    dump_as=list,
):
    generic, done, loop, finished = (
        c.label(prefix) for prefix in ("generic_iterable", "list_ready", "list_loop", "list_finished")
    )
    result = c.slot(owned=True)
    # Capture an outer loop before any branch can enter the generic path.
    cached_loop = output_type in (list, tuple) and c.reserve_loop_registers(nested=True)
    check_sequence_type(c, input_type, generic)
    if loading and strict_coercion:
        check_sequence_mapping(c, input_type)
    size = c.slot()
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.var_size]), "mov rax, [rax+16]  # initial list length")
    c.asm.store(size)
    reserved = c.call_c("PySet_New", Immediate(0)) if output_type in (set, frozenset) else c.reserve_list(size)
    c.transfer(reserved, result)
    index = c.slot()
    c.asm.emit(b"\x31\xc0", "xor eax, eax")
    c.asm.store(index)
    state = c.lazy_call(ErrorState) if debug_trail != DebugTrail.DISABLE else None
    borrowed_item = borrows_sequence_item(mapper)
    initialize_sequence_loop(c, index, result, cached_loop)
    c.asm.label(loop)
    # Re-read length and items after every callback. Python list iterators
    # also observe appends, deletions, replacements, and reallocations.
    load_sequence_item(c, index, input_type, cached_loop, finished)
    item = capture_sequence_item(c, borrowed_item)
    if mapper is as_is_stub:
        value = item
    elif debug_trail == DebugTrail.DISABLE:
        value = c.inline_call(mapper, item, consume_data=True, borrow_data=borrowed_item)
        if value != item and not borrowed_item:
            c.release(item, nonnull=True)
    else:
        boxed_index = c.lazy_c_call("PyLong_FromSsize_t", index)
        value = c.inline_call(
            mapper, item, partial(handle_error, debug_trail, loading), state, boxed_index,
            consume_data=True, borrow_data=borrowed_item,
        )
        if value != item and not borrowed_item:
            c.release(item, nonnull=True)
    failed, next_item = c.label("failed_element"), c.label("next_element")
    if debug_trail != DebugTrail.DISABLE and mapper is not as_is_stub:
        c.branch_if(value, MISSING, failed)
        c.cold_handlers.append(partial(skip_failed_sequence_item, c, value, failed, next_item))
    append_mapped_item(c, result, value, output_type, cached_target=cached_loop)
    c.asm.label(next_item)
    advance_sequence_index(c, index, cached_loop)
    c.asm.jump(loop)
    c.asm.label(finished)
    c.finish_lazy_state(state, partial(finish_iterable, origin, loading), "no_list_errors")
    if output_type is tuple:
        converted = c.list_as_tuple(result)
        c.release(result)
        c.transfer(converted, result)
    elif output_type is frozenset:
        converted = c.call_c("PyFrozenSet_New", result)
        c.release(result)
        c.transfer(converted, result)
    c.asm.jump(done)
    c.fallback_result(result, fallback, generic, done)
    c.release_loop_registers(reserved=cached_loop)
    return result


def initialize_sequence_loop(c, index, result, cached_loop):
    if cached_loop:
        c.asm.load(12, index)
        c.asm.load(13, c.data)
        c.asm.load(14, result)
        c.asm.emit(b"\x45\x31\xff", "xor r15d, r15d  # written elements")


def skip_failed_sequence_item(c, value, failed, next_item):
    c.asm.label(failed)
    c.release(value, nonnull=True)
    c.asm.jump(next_item)


def borrows_sequence_item(mapper):
    from adaptix._internal.morphing.native.x86_64.scalar import get_program  # noqa: PLC0415

    # These CPython versions defer automatic GC until the evaluator runs.
    # Exact builtin container copies execute no Python and keep the GIL;
    # their enclosing sequence owns the input until the copy finishes.
    # The union program retains inputs before any other converter or fallback.
    return (
        sys.version_info[:2] in {(3, 13), (3, 14), (3, 15)}
        and getattr(get_program(mapper), "supports_borrowing", False)
    )


def capture_sequence_item(c, borrowed):
    if not borrowed:
        return c.copy_loaded_reference()
    item = c.slot()
    c.asm.store(item)
    return item


def load_sequence_item(c, index, input_type, cached_loop, finished):
    if cached_loop:
        c.asm.emit(b"\x4d\x3b\x65" + bytes([c.layout.var_size]), "cmp r12, [r13+16]  # current input length")
    else:
        c.asm.load(0, index)
        c.asm.load(11, c.data)
        c.asm.emit(b"\x49\x3b\x43" + bytes([c.layout.var_size]), "cmp rax, [r11+16]  # current input length")
    c.asm.jump(finished, "ae")
    load_sequence_items(c, 1, 13 if cached_loop else 11, input_type)
    if cached_loop:
        c.asm.emit(b"\x4a\x8b\x04\xe1", "mov rax, [rcx+r12*8]")
    else:
        c.asm.emit(b"\x48\x8b\x04\xc1", "mov rax, [rcx+rax*8]")


def advance_sequence_index(c, index, cached_loop):
    if cached_loop:
        c.asm.emit(b"\x49\xff\xc4", "inc r12")
        c.asm.store(index, 12)
    else:
        c.asm.load(0, index)
        c.asm.emit(b"\x48\xff\xc0", "inc rax")
        c.asm.store(index)


def append_mapped_item(c, result, value, output_type, *, cached_target=False):
    if output_type in (set, frozenset):
        c.call_c("PySet_Add", result, value, result="int")
        c.release(value, nonnull=True)
    else:
        c.append_list(result, value, cached_target=cached_target)


def map_iterator(
    c, *, origin, mapper, fallback, debug_trail, loading, strict_coercion, output_type=list, dump_as=list,
):
    if loading and strict_coercion:
        from adaptix._internal.morphing import iterable_provider  # noqa: PLC0415

        frozen, checked = c.label("frozen_mapping_check"), c.label("set_mapping_checked")
        c.branch_if_type(c.data, frozenset, frozen)
        check_list_mapping(c, input_type=set, module=iterable_provider, attribute="CollectionsMapping")
        c.asm.jump(checked)
        c.asm.label(frozen)
        check_list_mapping(c, input_type=frozenset, module=iterable_provider, attribute="CollectionsMapping")
        c.asm.label(checked)
    size = c.slot()
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.set_used]), "load builtin set length")
    c.asm.store(size)
    direct_tuple = output_type is tuple and tuple_item_offset() is not None
    result, written = reserve_iterator_output(c, size, direct_tuple)
    iterator = c.call_c("PyObject_GetIter", c.data)
    index = c.slot()
    c.asm.emit(b"\x31\xc0", "zero iterator index")
    c.asm.store(index)
    state = c.lazy_call(ErrorState) if debug_trail != DebugTrail.DISABLE else None
    loop, ended, failed, next_item = (
        c.label(prefix) for prefix in ("iterator_map_loop", "iterator_map_end", "iterator_item_failed", "iterator_next")
    )
    c.asm.label(loop)
    item = c.call_c("PyIter_Next", iterator, error_label=ended)
    value = (
        c.inline_call(mapper, item, partial(handle_error, debug_trail, loading), state,
                      c.lazy_c_call("PyLong_FromSsize_t", index), consume_data=True)
        if state is not None else c.inline_call(mapper, item, consume_data=True)
    )
    if value != item:
        c.release(item, nonnull=True)
    if state is not None:
        c.branch_if(value, MISSING, failed)
    if direct_tuple:
        append_tuple_item(c, result, value, written)
    else:
        c.append_list(result, value)
    c.asm.jump(next_item)
    c.asm.label(failed)
    c.release(value)
    c.asm.label(next_item)
    c.asm.load(0, index)
    c.asm.emit(b"\x48\xff\xc0", "advance iterator index")
    c.asm.store(index)
    c.asm.jump(loop)
    c.asm.label(ended)
    finish_iterator_mapping(c, iterator, state, origin, loading)
    if direct_tuple:
        finish_tuple_output(c, result, written)
    elif output_type is not list:
        function = {tuple: "PyList_AsTuple", set: "PySet_New", frozenset: "PyFrozenSet_New"}[output_type]
        converted = c.list_as_tuple(result) if output_type is tuple else c.call_c(function, result)
        c.release(result)
        c.transfer(converted, result)
    return result


def finish_iterator_mapping(c, iterator, state, origin, loading):
    error = c.call_c("PyErr_Occurred", result="pointer")
    c.branch_if_null(error, c.call_error_label, invert=True)
    c.release(iterator)
    c.finish_lazy_state(state, partial(finish_iterable, origin, loading), "iterator_no_errors")


def reserve_iterator_output(c, size, direct_tuple):
    if not direct_tuple:
        return c.reserve_list(size), None
    result = c.call_c("PyTuple_New", size)
    c.call_c("PyObject_GC_UnTrack", result, result="void")
    written = c.slot()
    c.asm.emit(b"\x31\xc0", "zero tuple output length")
    c.asm.store(written)
    return result, written


def append_tuple_item(c, target, value, written):
    grow, ready, done = c.label("grow_tuple"), c.label("tuple_capacity_ready"), c.label("tuple_item_written")
    c.asm.load(7, target)
    c.asm.load(0, written)
    c.asm.emit(b"\x48\x3b\x47" + bytes([c.layout.var_size]), "check private tuple capacity")
    c.asm.jump(grow, "ae")
    c.asm.label(ready)
    c.asm.load(11, value)
    c.asm.emit(b"\x4c\x89\x5c\xc7" + bytes([tuple_item_offset()]), "transfer element into private tuple")
    c.asm.emit(b"\x48\xff\xc0", "advance tuple output length")
    c.asm.store(written)
    c.asm.clear(value)
    c.asm.jump(done)
    c.asm.label(grow)
    size = c.slot()
    c.asm.emit(b"\x48\x89\xc1\x48\xd1\xe9\x48\x8d\x4c\x08\x04", "grow private tuple capacity by half plus four")
    c.asm.store(size, 1)
    c.call_c("_PyTuple_Resize", Address(target), size, result="int")
    c.call_c("PyObject_GC_UnTrack", target, result="void")
    c.asm.load(7, target)
    c.asm.load(0, written)
    c.asm.jump(ready)
    c.asm.label(done)
    c.asm.mark_clear(value)


def finish_tuple_output(c, target, written):
    sized, empty = c.label("tuple_output_sized"), c.label("tuple_output_empty")
    c.asm.load(0, written)
    c.asm.load(7, target)
    c.asm.emit(b"\x48\x3b\x47" + bytes([c.layout.var_size]), "check final private tuple length")
    c.asm.jump(sized, "z")
    c.call_c("_PyTuple_Resize", Address(target), written, result="int")
    c.call_c("PyObject_GC_UnTrack", target, result="void")
    c.asm.label(sized)
    c.branch_if_null(written, empty)
    c.call_c("PyObject_GC_Track", target, result="void")
    c.asm.label(empty)


def copy_scalar_list(  # noqa: PLR0915
    c, spec, fallback, *, loading, strict_coercion, input_type=list, output_type=list,
    slow_mapper=None,
):
    types, nullable = spec
    generic, done, loop, finished, failed = (
        c.label(prefix) for prefix in (
            "list_copy_slow", "list_copy_done", "list_copy_loop", "list_copy_end", "list_copy_failed",
        )
    )
    result = c.slot(owned=True)
    check_sequence_type(c, input_type, generic)
    if loading and strict_coercion:
        check_sequence_mapping(c, input_type)
    if not types and not nullable:
        copied = copy_identity_sequence(c, input_type, output_type)
        c.transfer(copied, result)
        c.asm.jump(done)
        return c.fallback_result(result, fallback, generic, done)
    size = c.slot()
    if slow_mapper is not None:
        branch_if_initial_integer(c, input_type, generic)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.var_size]), "mov rax, [rax+16]")
    c.asm.store(size)
    reserved = c.call_c("PyTuple_New", size) if output_type is tuple else c.reserve_list(size)
    c.transfer(reserved, result)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x4c\x8b\x40" + bytes([c.layout.var_size]), "mov r8, [rax+16]")
    load_sequence_items(c, 2, 0, input_type)
    c.asm.load(1, size)
    c.asm.emit(b"\x49\x39\xc8", "cmp r8, rcx  # allocation callback grew input")
    c.asm.jump(generic, "nz" if output_type is tuple else "a")
    c.asm.load(0, result)
    load_sequence_items(c, 6, 0, output_type)
    c.asm.emit(b"\x31\xc9", "xor ecx, ecx")
    if types:
        c.load(9, c.constant(types[0]))
    if len(types) > 1:
        c.load(10, c.constant(types[1]))
    if nullable:
        c.load(11, c.constant(None))
    c.asm.label(loop)
    c.asm.emit(b"\x4c\x39\xc1", "cmp rcx, r8")
    c.asm.jump(finished, "ae")
    c.asm.emit(b"\x48\x8b\x3c\xca", "mov rdi, [rdx+rcx*8]")
    if types or nullable:
        check_scalar_list_item(c, types, nullable, failed)
    c.incref_rdi(nonnull=True)
    c.asm.emit(b"\x48\x89\x3c\xce\x48\xff\xc1", "mov [rsi+rcx*8], rdi; inc rcx")
    c.asm.jump(loop)
    c.asm.label(finished)
    if output_type is list:
        c.asm.load(0, result)
        c.asm.emit(b"\x48\x89\x48" + bytes([c.layout.var_size]), "mov [rax+16], rcx  # publish initialized elements")
    c.asm.jump(done)
    c.asm.label(failed)
    if output_type is list:
        c.asm.load(0, result)
        c.asm.emit(b"\x48\x89\x48" + bytes([c.layout.var_size]), "mov [rax+16], rcx")
    c.asm.label(generic)
    c.release(result)
    converted = (
        c.call(fallback, c.data) if slow_mapper is None
        else map_list(c, **vars(slow_mapper), input_type=input_type, output_type=output_type)
    )
    c.transfer(converted, result)
    c.asm.label(done)
    return result


def copy_identity_sequence(c, input_type, output_type, *, destination=None):
    if input_type is list:
        if output_type is tuple:
            return c.call_c("PyList_AsTuple", c.data, destination=destination)
        return c.copy_list(c.data, destination=destination)
    if output_type is list:
        return c.call_c("PySequence_List", c.data, destination=destination)
    size, items = c.slot(), c.slot()
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x48" + bytes([c.layout.var_size]), "load identity tuple length")
    c.asm.store(size, 1)
    load_sequence_items(c, 1, 0, tuple)
    c.asm.store(items, 1)
    if hasattr(ctypes.pythonapi, "_PyTuple_FromArray"):
        return c.call_c("_PyTuple_FromArray", items, size, destination=destination)
    snapshot = c.call_c("PySequence_List", c.data)
    result = c.list_as_tuple(snapshot)
    c.release(snapshot)
    if destination is not None:
        c.transfer(result, destination)
        return destination
    return result


def branch_if_initial_integer(c, input_type, generic):
    empty = c.label("empty_scalar_sequence")
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x83\x78" + bytes([c.layout.var_size]) + b"\x00", "check for an initial coercion candidate")
    c.asm.jump(empty, "z")
    if input_type is list:
        c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.list_items]) + b"\x48\x8b\x00", "load initial list member")
    else:
        c.asm.emit(b"\x48\x8b\x40" + bytes([tuple_item_offset()]), "load initial tuple member")
    c.load(11, c.constant(int))
    c.asm.emit(b"\x4c\x39\x58" + bytes([c.layout.object_type]), "check whether the mapper must convert an integer")
    c.asm.jump(generic, "z")
    c.asm.label(empty)


def check_scalar_list_item(c, types, nullable, failed):
    # This region calls no Python and cannot release the GIL. The input list
    # owns rdi until the loop retains it directly for the output list.
    accepted = c.label("list_item_ok")
    if nullable:
        c.asm.emit(b"\x4c\x39\xdf", "cmp rdi, r11")
        c.asm.jump(accepted, "z")
    for index, cls in enumerate(types):
        if index < 2:  # noqa: PLR2004
            register = 9 + index
            c.asm.emit(b"\x4c\x39" + bytes([0x4F + index * 8, 8]), f"cmp [rdi+8], r{register}")
        else:
            c.load(0, c.constant(cls))
            c.asm.emit(b"\x48\x39\x47" + bytes([c.layout.object_type]), "cmp [rdi+8], rax")
        if index == len(types) - 1:
            c.asm.jump(failed, "nz")
        else:
            c.asm.jump(accepted, "z")
    if not types:
        c.asm.jump(failed)
    c.asm.label(accepted)
