import ctypes
import gc
import struct
import sys
from dataclasses import dataclass
from typing import Any

from adaptix._internal.code_tools.cpython_layout.selection import require_cpython_layout


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
    layout = require_cpython_layout()
    from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
        inline_index,
        pointer,
        supports_attribute_cache,
    )

    cls = type("_NativeDictTemplate", (), {"__module__": __name__})
    owner = None
    data = dict.fromkeys(names)
    tracked_copies = (
        sys.version_info[:2] in {(3, 14), (3, 15)} and gc.is_tracked(data.copy()) and gc.is_tracked({}.copy())
    )
    if len(names) < 30 and supports_attribute_cache():  # noqa: PLR2004
        # CPython gradually reduces the inline capacity of a fresh class.
        # Warm this private class until only the required keys and one spare
        # entry remain, avoiding a 30-value buffer in every output dictionary.
        for _ in range(32):
            owner = cls()
            data = vars(owner)
            for name in names:
                data[name] = None
        values = pointer(id(data) + layout.offset("dict_values"))
        indices = tuple(inline_index(cls, name) for name in names)
        if values and all(index is not None for index in indices):
            keys = pointer(id(data) + layout.offset("dict_keys"))
            index_bytes = ctypes.c_uint8.from_address(keys + layout.offset("keys_index_bytes")).value
            concrete = tuple(index for index in indices if index is not None)
            if all(
                pointer(values + layout.offset("values_items") + index * ctypes.sizeof(ctypes.c_void_p)) == id(None)
                for index in concrete
            ):
                return DictionaryTemplate(
                    data=data,
                    owner=owner,
                    kind=2,
                    index_bytes=index_bytes,
                    key_offsets=tuple(
                        layout.offset("keys_indices") + (1 << index_bytes) + index * layout.offset("unicode_entry_size")
                        for index in concrete
                    ),
                    value_offsets=tuple(index * 8 for index in concrete),
                    tracked_copies=tracked_copies,
                    capacity=ctypes.c_uint8.from_address(values + layout.offset("values_capacity")).value,
                    keys_pointer=keys,
                    # Keep the original type even if the carrier's __class__
                    # changes. Its cached-key reference prevents address reuse.
                    keys_owner=cls,
                )
    data = dict.fromkeys(names)
    keys = pointer(id(data) + layout.offset("dict_keys"))
    index_bytes = ctypes.c_uint8.from_address(keys + layout.offset("keys_index_bytes")).value
    key_offsets = tuple(
        layout.offset("keys_indices") + (1 << index_bytes) + index * layout.offset("unicode_entry_size")
        for index in range(len(names))
    )
    return DictionaryTemplate(
        data=data, owner=None, kind=1, index_bytes=index_bytes,
        key_offsets=key_offsets,
        value_offsets=tuple(offset + layout.offset("unicode_entry_value") for offset in key_offsets),
        tracked_copies=tracked_copies,
    )

def guard_dictionary_value(c, namespace, key, expected, missing, generic):
    layout = c.layout
    from adaptix._internal.code_tools.native_access import pointer, size  # noqa: PLC0415

    lookup, done = c.label("namespace_lookup"), c.label("namespace_checked")
    keys = pointer(id(namespace) + layout.dict_keys)
    if (
        not pointer(id(namespace) + layout.dict_values)
        and ctypes.c_uint8.from_address(keys + layout.keys_kind).value == 1
    ):
        entries = keys + layout.keys_indices + (1 << ctypes.c_uint8.from_address(keys + layout.keys_index_bytes).value)
        for index in range(size(keys + layout.keys_nentries)):
            address = pointer(entries + index * layout.unicode_entry_size)
            if address and ctypes.cast(address, ctypes.py_object).value == key:
                stored_key = ctypes.cast(address, ctypes.py_object).value
                c.load(0, c.constant(namespace))
                c.asm.emit(
                    b"\x48\x83\x78" + bytes([c.layout.dict_values]) + b"\x00", "check combined constant dictionary",
                )
                c.asm.jump(lookup, "nz")
                c.asm.emit(
                    b"\x48\x8b\x40" + bytes([c.layout.dict_keys]) + b"\x80\x78" + bytes([c.layout.keys_kind]) + b"\x01",
                    "check constant dictionary Unicode keys",
                )
                c.asm.jump(lookup, "nz")
                c.asm.emit(
                    b"\x48\x81\x78" + bytes([layout.keys_nentries]) + struct.pack("<i", index),
                    "check cached constant dictionary index",
                )
                c.asm.jump(lookup, "be")
                c.asm.emit(
                    b"\x0f\xb6\x48" + bytes([c.layout.keys_index_bytes]) + b"\xba\x01\x00\x00\x00\x48\xd3\xe2",
                    "constant dictionary index bytes",
                )
                c.asm.emit(b"\x48\x8d\x44\x10" + bytes([c.layout.keys_indices]), "constant dictionary entries")
                c.load(11, c.constant(stored_key))
                c.asm.emit(
                    b"\x4c\x39\x98" + struct.pack("<i", index * layout.unicode_entry_size),
                    "check constant dictionary key",
                )
                c.asm.jump(lookup, "nz")
                c.load(11, c.constant(expected))
                c.asm.emit(
                    b"\x4c\x39\x98" + struct.pack("<i", index * layout.unicode_entry_size + layout.unicode_entry_value),
                    "check constant dictionary value",
                )
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
