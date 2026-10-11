import ctypes
import sys
from dataclasses import dataclass
from functools import cache

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.morphing.native.plan import DictPlan
from adaptix._internal.morphing.native.registry import identity_spec

LAYOUT = get_cpython_layout()

@cache
def general_entries_supported():
    key, value = 1001, object()
    probe = {key: value}
    keys = ctypes.c_void_p.from_address(id(probe) + LAYOUT.dict_keys).value
    if not keys or ctypes.c_uint8.from_address(keys + LAYOUT.keys_kind).value != 0:
        return False
    entries = keys + LAYOUT.keys_indices + (1 << ctypes.c_uint8.from_address(keys + LAYOUT.keys_index_bytes).value)
    return (
        ctypes.c_ssize_t.from_address(keys + LAYOUT.keys_nentries).value == 1
        and ctypes.c_void_p.from_address(entries + LAYOUT.general_entry_key).value == id(key)
        and ctypes.c_void_p.from_address(entries + LAYOUT.general_entry_value).value == id(value)
    )


def build_dict_program(plan: DictPlan, c):
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        return None
    from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.dict_mapper import (  # noqa: PLC0415
        DictProgram,
        dictionary_iterator_supported,
    )
    from adaptix._internal.morphing.native.x86_64.iterable import tuple_item_offset  # noqa: PLC0415

    if not c.has_validated_object_header or not supports_dictionary_cache():
        return None
    key_spec, value_spec = identity_spec(plan.key_mapper), identity_spec(plan.value_mapper)
    if key_spec is None or value_spec is None:
        c.name = "native_dict_mapper"
        return (
            DictProgram(**vars(plan)) if dictionary_iterator_supported() and tuple_item_offset() is not None else None
        )
    if plan.loading and not general_entries_supported():
        return None
    return DictCopyProgram(**vars(plan))


def copy_dictionary(c, key_spec, value_spec, fallback, loading):
    from adaptix._internal.morphing.native.x86_64.dict_mapper import check_dictionary_type  # noqa: PLC0415

    generic, done = c.label("dict_copy_slow"), c.label("dict_copy_done")
    result = c.slot(owned=True)
    check_dictionary_type(c, generic)
    if loading:
        copy = c.label("dict_copy_without_key_callbacks")
        c.asm.load(0, c.data)
        c.asm.emit(
            b"\x48\x8b\x50" + bytes([c.layout.dict_keys]) + b"\x80\x7a" + bytes([c.layout.keys_kind]) + b"\x00",
            "check general dictionary keys",
        )
        c.asm.jump(copy, "nz")
        c.asm.emit(b"\x48\x8b\x48" + bytes([c.layout.dict_used]) + b"\x48\x8d\x0c\x49", "live entries * 3")
        c.asm.emit(
            b"\x48\x8b\x42" + bytes([c.layout.keys_nentries]) + b"\x48\x01\xc0\x48\x39\xc1",
            "compare with total entries * 2",
        )
        # PyDict_Copy reinserts sparse general keys, potentially calling their
        # equality methods before our type validation. Dense tables are cloned.
        c.asm.jump(generic, "be")
        c.asm.label(copy)
    value = c.call_c("PyDict_Copy", c.data)
    c.transfer(value, result)
    if loading:
        finished, unicode_table = c.label("dict_checked"), c.label("dict_unicode_table")
        c.asm.load(0, result)
        c.asm.emit(b"\x48\x8b\x50" + bytes([c.layout.dict_keys]), "mov rdx, [rax+32]  # keys")
        c.asm.emit(b"\x4c\x8b\x42" + bytes([c.layout.keys_nentries]) + b"\x4d\x85\xc0", "mov r8, [rdx+24]; test r8, r8")
        c.asm.jump(finished, "z")
        c.asm.emit(
            b"\x48\x83\x78" + bytes([c.layout.dict_values]) + b"\x00",
            "cmp QWORD PTR [rax+40], 0  # combined dictionary",
        )
        c.asm.jump(generic, "nz")
        c.asm.emit(
            b"\x80\x7a" + bytes([c.layout.keys_kind]) + b"\x01", "cmp BYTE PTR [rdx+10], 1  # exact Unicode keys",
        )
        c.asm.jump(unicode_table, "z")
        c.asm.emit(b"\x80\x7a" + bytes([c.layout.keys_kind]) + b"\x00", "cmp BYTE PTR [rdx+10], 0  # general keys")
        c.asm.jump(generic, "nz")
        validate_entries(
            c, key_spec, value_spec, stride=c.layout.general_entry_size, generic=generic, finished=finished,
        )
        c.asm.label(unicode_table)
        if key_spec[0] and str not in key_spec[0]:
            c.asm.jump(generic)
        validate_entries(c, None, value_spec, stride=c.layout.unicode_entry_size, generic=generic, finished=finished)
        c.asm.label(finished)
    c.asm.jump(done)
    return c.fallback_result(result, fallback, generic, done, cleanup=(result,))


@dataclass(frozen=True)
class DictCopyProgram(DictPlan):
    def emit(self, c):
        return copy_dictionary(
            c, identity_spec(self.key_mapper), identity_spec(self.value_mapper), self.fallback, self.loading,
        )


def validate_entries(c, key_spec, value_spec, *, stride, generic, finished):
    loop, accepted = c.label("dict_check_entry"), c.label("dict_entry_ok")
    c.asm.emit(
        b"\x0f\xb6\x4a" + bytes([c.layout.keys_index_bytes]) + b"\xb8\x01\x00\x00\x00\x48\xd3\xe0",
        "load index array size",
    )
    c.asm.emit(b"\x48\x8d\x54\x02" + bytes([c.layout.keys_indices]), "lea rdx, [rdx+rax+32]  # entries")
    if value_spec[0]:
        c.load(9, c.constant(value_spec[0][0]))
    if key_spec is not None and key_spec[0]:
        c.load(10, c.constant(key_spec[0][0]))
    if value_spec[1] or (key_spec is not None and key_spec[1]):
        c.load(11, c.constant(None))
    c.asm.label(loop)
    value_offset = (
        c.layout.general_entry_value if stride == c.layout.general_entry_size else c.layout.unicode_entry_value
    )
    c.asm.emit(b"\x48\x8b\x42" + bytes([value_offset]) + b"\x48\x85\xc0", "load entry value; test rax, rax")
    c.asm.jump(accepted, "z")
    key_offset = c.layout.general_entry_key if stride == c.layout.general_entry_size else c.layout.unicode_entry_key
    value_register, key_register = 9, 10
    for spec, offset, register in ((value_spec, value_offset, value_register), (key_spec, key_offset, key_register)):
        if spec is None or (not spec[0] and not spec[1]):
            continue
        valid = c.label("dict_scalar_ok")
        c.asm.emit(b"\x48\x8b\x42" + bytes([offset]), "load dictionary scalar")
        if spec[1]:
            c.load(11, c.constant(None))
            c.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11  # nullable")
            c.asm.jump(valid, "z")
        for index, cls in enumerate(spec[0]):
            if index == 0:
                c.asm.emit(
                    b"\x4c\x39" + bytes([0x48 if register == value_register else 0x50, c.layout.object_type]),
                    "check exact scalar type",
                )
            else:
                c.load(11, c.constant(cls))
                c.asm.emit(b"\x4c\x39\x58" + bytes([c.layout.object_type]), "check exact scalar type")
            c.asm.jump(valid, "z")
        c.asm.jump(generic)
        c.asm.label(valid)
    c.asm.label(accepted)
    c.asm.emit(b"\x48\x83\xc2" + bytes([stride]) + b"\x49\xff\xc8", f"add rdx, {stride}; dec r8")
    c.asm.jump(loop, "nz")
    c.asm.jump(finished)
