import ctypes
import gc
import struct
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DictionaryTemplate:
    data: dict[str, None]
    owner: Any
    kind: int
    index_bytes: int
    key_offsets: tuple[int, ...]
    value_offsets: tuple[int, ...]
    tracked_copies: bool
    capacity: int = 0
    keys_pointer: int = 0
    keys_owner: type | None = None


def create_dictionary_template(names: tuple[str, ...]) -> DictionaryTemplate:
    from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
        inline_index,
        pointer,
        supports_attribute_cache,
    )

    cls = type("_NativeDictTemplate", (), {"__module__": __name__})
    owner = None
    data = dict.fromkeys(names)
    tracked_copies = sys.version_info[:2] == (3, 14) and gc.is_tracked(data.copy()) and gc.is_tracked({}.copy())
    if len(names) < 30 and supports_attribute_cache():  # noqa: PLR2004
        # CPython gradually reduces the inline capacity of a fresh class.
        # Warm this private class until only the required keys and one spare
        # entry remain, avoiding a 30-value buffer in every output dictionary.
        for _ in range(32):
            owner = cls()
            data = vars(owner)
            for name in names:
                data[name] = None
        values = pointer(id(data) + 40)
        indices = tuple(inline_index(cls, name) for name in names)
        if values and all(index is not None for index in indices):
            keys = pointer(id(data) + 32)
            index_bytes = ctypes.c_uint8.from_address(keys + 9).value
            concrete = tuple(index for index in indices if index is not None)
            if all(pointer(values + 8 + index * 8) == id(None) for index in concrete):
                return DictionaryTemplate(
                    data=data, owner=owner, kind=2, index_bytes=index_bytes,
                    key_offsets=tuple(32 + (1 << index_bytes) + index * 16 for index in concrete),
                    value_offsets=tuple(index * 8 for index in concrete),
                    tracked_copies=tracked_copies,
                    capacity=ctypes.c_uint8.from_address(values).value,
                    keys_pointer=keys,
                    # Keep the original type even if the carrier's __class__
                    # changes. Its cached-key reference prevents address reuse.
                    keys_owner=cls,
                )
    data = dict.fromkeys(names)
    keys = pointer(id(data) + 32)
    index_bytes = ctypes.c_uint8.from_address(keys + 9).value
    key_offsets = tuple(32 + (1 << index_bytes) + index * 16 for index in range(len(names)))
    return DictionaryTemplate(
        data=data, owner=None, kind=1, index_bytes=index_bytes,
        key_offsets=key_offsets, value_offsets=tuple(offset + 8 for offset in key_offsets),
        tracked_copies=tracked_copies,
    )

def guard_dictionary_value(c, namespace, key, expected, missing, generic):
    from adaptix._internal.code_tools.native_access import pointer, size  # noqa: PLC0415

    lookup, done = c.label("namespace_lookup"), c.label("namespace_checked")
    keys = pointer(id(namespace) + 32)
    if not pointer(id(namespace) + 40) and ctypes.c_uint8.from_address(keys + 10).value == 1:
        entries = keys + 32 + (1 << ctypes.c_uint8.from_address(keys + 9).value)
        for index in range(size(keys + 24)):
            address = pointer(entries + index * 16)
            if address and ctypes.cast(address, ctypes.py_object).value == key:
                stored_key = ctypes.cast(address, ctypes.py_object).value
                c.load(0, c.constant(namespace))
                c.asm.emit(b"\x48\x83\x78\x28\x00", "check combined constant dictionary")
                c.asm.jump(lookup, "nz")
                c.asm.emit(b"\x48\x8b\x40\x20\x80\x78\x0a\x01", "check constant dictionary Unicode keys")
                c.asm.jump(lookup, "nz")
                c.asm.emit(b"\x48\x81\x78\x18" + struct.pack("<i", index), "check cached constant dictionary index")
                c.asm.jump(lookup, "be")
                c.asm.emit(b"\x0f\xb6\x48\x09\xba\x01\x00\x00\x00\x48\xd3\xe2", "constant dictionary index bytes")
                c.asm.emit(b"\x48\x8d\x44\x10\x20", "constant dictionary entries")
                c.load(11, c.constant(stored_key))
                c.asm.emit(b"\x4c\x39\x98" + struct.pack("<i", index * 16), "check constant dictionary key")
                c.asm.jump(lookup, "nz")
                c.load(11, c.constant(expected))
                c.asm.emit(b"\x4c\x39\x98" + struct.pack("<i", index * 16 + 8), "check constant dictionary value")
                c.asm.jump(generic, "nz")
                c.asm.jump(done)
                break
    c.asm.label(lookup)
    value = c.call_c("PyDict_GetItemWithError", c.constant(namespace), c.constant(key), result="pointer")
    if expected is missing:
        c.branch_if_null(value, generic, invert=True)
        error = c.call_c("PyErr_Occurred", result="pointer")
        c.branch_if_null(error, c.call_error_label, invert=True)
    else:
        present = c.label("namespace_present")
        c.branch_if_null(value, present, invert=True)
        error = c.call_c("PyErr_Occurred", result="pointer")
        c.branch_if_null(error, c.call_error_label, invert=True)
        c.asm.jump(generic)
        c.asm.label(present)
        c.branch_if(value, expected, generic, invert=True)
    c.asm.label(done)
