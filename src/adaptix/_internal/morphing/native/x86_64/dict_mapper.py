import ctypes
from dataclasses import dataclass
from functools import cache, partial

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.native.plan import DictPlan
from adaptix._internal.morphing.native.registry import identity_spec
from adaptix._internal.morphing.native.runtime import ErrorState, dictionary_error, finish_dictionary
from adaptix._internal.morphing.native.x86_64.iterable import tuple_item_offset
from adaptix._internal.special_cases_optimization import as_is_stub

LAYOUT = get_cpython_layout()

class DictionarySubclassCache(ctypes.Structure):
    _fields_ = [("cls", ctypes.c_void_p), ("version", ctypes.c_uint32), ("enabled", ctypes.c_uint32)]

    def __init__(self):
        super().__init__()
        self.held_class = None

    def learn(self, data):
        from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
            GENERIC_GETTER,
            IS_SUBTYPE,
            LOOKUP,
            get_type_version,
            pointer,
        )

        cls = type(data)
        enabled = (
            type(cls) is type and IS_SUBTYPE(cls, dict)
            and pointer(id(cls) + LAYOUT.type_getattro) == GENERIC_GETTER
            and LOOKUP(cls, "items") is dict.items
        )
        self.enabled = 0
        self.held_class = cls
        self.cls = id(cls)
        self.version = get_type_version(cls)
        self.enabled = enabled


def check_dictionary_type(c, generic):
    accepted, guard, learn = (
        c.label(prefix) for prefix in ("dictionary_type_ok", "dictionary_subclass_guard", "dictionary_subclass_learn")
    )
    c.branch_if_type(c.data, dict, accepted)
    cache = DictionarySubclassCache()
    c.constants.append(cache)
    c.asm.label(guard)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.object_type]), "load dictionary subclass")
    c.asm.mov_imm(11, ctypes.addressof(cache))
    c.check_cached_type(learn)
    c.asm.emit(b"\x41\x83\x7b\x0c\x00", "check ordinary dictionary items lookup")
    c.asm.jump(generic, "z")
    namespace_pointer = c.call_c("_PyObject_GetDictPtr", c.data, result="pointer")
    c.branch_if_null(namespace_pointer, accepted)
    c.asm.load(0, namespace_pointer)
    c.asm.emit(b"\x48\x8b\x00\x48\x85\xc0", "load optional subclass attributes")
    c.asm.jump(accepted, "z")
    namespace = c.slot()
    c.asm.store(namespace)
    c.asm.emit(
        b"\x48\x8b\x50" + bytes([c.layout.dict_keys]) + b"\x80\x7a" + bytes([c.layout.keys_kind]) + b"\x00",
        "check exact Unicode attribute keys",
    )
    c.asm.jump(generic, "z")
    c.call_c("PyDict_Contains", namespace, c.constant("items"), result="pointer")
    c.asm.test_jump(0, c.call_error_label, "s", bits=32)
    c.asm.jump(generic, "nz")
    c.asm.jump(accepted)
    c.asm.label(learn)
    c.release(c.call(cache.learn, c.data))
    c.asm.jump(guard)
    c.asm.label(accepted)


@cache
def dictionary_iterator_supported():
    data = {"first": object(), "second": object()}
    iterator = iter(data.items())
    address = id(iterator)
    if (
        ctypes.c_void_p.from_address(address + LAYOUT.dictiter_dict).value != id(data)
        or ctypes.c_ssize_t.from_address(address + LAYOUT.dictiter_used).value != len(data)
        or ctypes.c_ssize_t.from_address(address + LAYOUT.dictiter_position).value != 0
        or ctypes.c_ssize_t.from_address(address + LAYOUT.dictiter_remaining).value != len(data)
    ):
        return False
    next(iterator)
    return (
        ctypes.c_ssize_t.from_address(address + LAYOUT.dictiter_position).value == 1
        and ctypes.c_ssize_t.from_address(address + LAYOUT.dictiter_remaining).value == 1
    )






@dataclass(frozen=True)
class DictProgram(DictPlan):
    def emit(self, c):  # noqa: PLR0915
        generic, done, loop, slow, ready, ended, next_item = (
            c.label(prefix) for prefix in (
                "dict_map_slow", "dict_map_done", "dict_map_loop", "dict_iterator_next",
                "dict_pair_ready", "dict_iterator_end", "dict_next_pair",
            )
        )
        result, key, value, iterator = (c.slot(owned=True) for _ in range(4))
        check_dictionary_type(c, generic)
        size, position, remaining = (c.slot() for _ in range(3))
        c.asm.load(0, c.data)
        c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.dict_used]), "load expected output dictionary size")
        c.asm.store(size)
        created = c.call_c("_PyDict_NewPresized", size)
        c.transfer(created, result)
        c.asm.load(0, c.data)
        c.asm.emit(
            b"\x48\x8b\x40" + bytes([c.layout.dict_used]) + b"\x48\x85\xc0", "capture current dictionary iterator size",
        )
        c.asm.store(size)
        c.asm.store(remaining)
        c.asm.jump(done, "z")
        c.asm.emit(b"\x31\xc0", "zero dictionary iterator position")
        c.asm.store(position)
        state = c.lazy_call(ErrorState) if self.debug_trail != DebugTrail.DISABLE else None
        success = c.label("dict_iterator_success")
        c.asm.label(loop)
        self.next_direct(c, iterator, key, value, size, position, remaining, slow, ready, loop, success)
        c.asm.label(slow)
        initialized = c.label("dictionary_iterator_initialized")
        c.branch_if_null(iterator, initialized, invert=True)
        view = c.call(dict.items, c.data)
        created = c.call_c("PyObject_GetIter", view)
        c.transfer(created, iterator)
        c.release(view)
        c.asm.load(0, iterator)
        for displacement, source in ((24, size), (32, position), (48, remaining)):
            c.asm.load(11, source)
            c.asm.emit(b"\x4c\x89\x58" + bytes([displacement]), "restore dictionary iterator state")
        c.asm.label(initialized)
        pair = c.call_c("PyIter_Next", iterator, error_label=ended)
        offset = tuple_item_offset()
        for target, displacement in ((key, offset), (value, offset + 8)):
            c.asm.load(0, pair)
            c.asm.emit(b"\x48\x8b\x40" + bytes([displacement]), "load dictionary pair member")
            retained = c.copy_loaded_reference()
            c.transfer(retained, target)
        c.release(pair)
        c.asm.label(ready)
        if self.debug_trail == DebugTrail.DISABLE:
            # Assignment evaluates its right-hand side before its subscript.
            mapped_value, value_owner = self.map_item(c, self.value_mapper, value, key, state, is_key=False)
            mapped_key, key_owner = self.map_item(c, self.key_mapper, key, key, state, is_key=True)
        else:
            mapped_key, key_owner = self.map_item(c, self.key_mapper, key, key, state, is_key=True)
            mapped_value, value_owner = self.map_item(c, self.value_mapper, value, key, state, is_key=False)
        if state is not None and self.debug_trail == DebugTrail.ALL:
            c.branch_if_null(state, next_item, invert=True)
        c.call_c("PyDict_SetItem", result, mapped_key, mapped_value, result="int")
        c.asm.label(next_item)
        for item in dict.fromkeys((value_owner, key_owner, value, key)):
            if item is not None:
                c.release(item)
        c.asm.jump(loop)
        c.asm.label(ended)
        error = c.call_c("PyErr_Occurred", result="pointer")
        c.branch_if_null(error, c.call_error_label, invert=True)
        c.asm.label(success)
        c.release(iterator)
        c.finish_lazy_state(state, partial(finish_dictionary, self.loading), "dict_no_errors")
        c.asm.jump(done)
        return c.fallback_result(result, self.fallback, generic, done)

    def map_item(self, c, mapper, data, key, state, *, is_key):
        if mapper is as_is_stub:
            return data, None
        spec = identity_spec(mapper)
        if is_key and spec is not None and str in spec[0]:
            return self.map_string_key(c, mapper, data, state)
        value = self.map_checked_item(c, mapper, data, key, state, is_key=is_key)
        return value, value

    def map_string_key(self, c, mapper, data, state):
        generic, done = c.label("dictionary_key_type_error"), c.label("dictionary_key_checked")
        argument, owner = c.slot(), c.slot(owned=True)
        c.branch_if_type(data, str, generic, invert=True)
        c.asm.load(0, data)
        c.asm.store(argument)
        c.asm.jump(done)
        c.asm.label(generic)
        value = self.map_checked_item(c, mapper, data, data, state, is_key=True)
        c.transfer(value, owner)
        c.asm.load(0, owner)
        c.asm.store(argument)
        c.asm.label(done)
        return argument, owner

    def map_checked_item(self, c, mapper, data, key, state, *, is_key):
        if state is None:
            return c.inline_call(mapper, data)
        return c.inline_call(
            mapper, data, partial(dictionary_error, self.debug_trail, self.loading, is_key), state, key,
        )

    def next_direct(self, c, iterator, key, value, size, position, remaining, slow, ready, loop, ended):
        # Keep CPython's size, position and remaining count. Allocate its actual
        # iterator only when the table or a mutation needs the general path.
        c.branch_if_null(iterator, slow, invert=True)
        c.asm.load(2, c.data)
        c.asm.load(1, size)
        c.asm.emit(b"\x48\x3b\x4a" + bytes([c.layout.dict_used]), "check dictionary size against iterator")
        c.asm.jump(slow, "nz")
        c.asm.emit(b"\x48\x83\x7a" + bytes([c.layout.dict_values]) + b"\x00", "check combined dictionary")
        c.asm.jump(slow, "nz")
        c.asm.emit(b"\x48\x8b\x52" + bytes([c.layout.dict_keys]), "load current dictionary keys")
        c.asm.load(9, position)
        c.asm.emit(b"\x4c\x3b\x4a" + bytes([c.layout.keys_nentries]), "check iterator position against entries")
        c.asm.jump(ended, "ae")
        c.asm.emit(
            b"\x0f\xb6\x4a" + bytes([c.layout.keys_index_bytes]) + b"\x41\xba\x01\x00\x00\x00\x49\xd3\xe2",
            "index array size",
        )
        c.asm.emit(b"\x4a\x8d\x54\x12" + bytes([c.layout.keys_indices]), "dictionary entries pointer")
        unicode, loaded = c.label("mapped_dictionary_unicode"), c.label("mapped_dictionary_entry_loaded")
        c.asm.load(0, c.data)
        c.asm.emit(
            b"\x48\x8b\x40" + bytes([c.layout.dict_keys]) + b"\x80\x78" + bytes([c.layout.keys_kind]) + b"\x01",
            "check Unicode dictionary entries",
        )
        c.asm.jump(unicode, "z")
        c.asm.emit(b"\x80\x78" + bytes([c.layout.keys_kind]) + b"\x00", "check general dictionary entries")
        c.asm.jump(slow, "nz")
        c.asm.emit(b"\x4f\x8d\x0c\x49\x49\xc1\xe1\x03", "general entry position * 24")
        c.asm.emit((
                       b"\x4e\x8b\x44\x0a"
                       + bytes([c.layout.general_entry_value])
                       + b"\x4e\x8b\x54\x0a"
                       + bytes([c.layout.general_entry_key])
                   ), "load general dictionary key and value")
        c.asm.jump(loaded)
        c.asm.label(unicode)
        c.asm.emit(
            b"\x49\xc1\xe1" + bytes([c.layout.unicode_entry_size.bit_length() - 1]), "scale Unicode entry position",
        )
        c.asm.emit(
            b"\x4e\x8b\x44\x0a" + bytes([c.layout.unicode_entry_value]) + b"\x4e\x8b\x14\x0a",
            "load Unicode dictionary key and value",
        )
        c.asm.label(loaded)
        c.asm.emit(b"\x4d\x85\xc0", "check live dictionary entry")
        present = c.label("dict_entry_present")
        c.asm.jump(present, "nz")
        c.asm.load(0, position)
        c.asm.emit(b"\x48\xff\xc0", "skip deleted entry in iterator")
        c.asm.store(position)
        c.asm.jump(loop)
        c.asm.label(present)
        c.asm.load(0, remaining)
        c.asm.test_jump(0, slow)
        c.asm.emit(b"\x48\xff\xc8", "decrement remaining elements")
        c.asm.store(remaining)
        c.asm.load(0, position)
        c.asm.emit(b"\x48\xff\xc0", "advance dictionary iterator")
        c.asm.store(position)
        for instruction, target in ((b"\x4c\x89\xd7", key), (b"\x4c\x89\xc7", value)):
            c.asm.emit(instruction, "retain dictionary member in rdi")
            c.incref_rdi(nonnull=True)
            c.asm.store(target, 7)
        c.asm.jump(ready)
