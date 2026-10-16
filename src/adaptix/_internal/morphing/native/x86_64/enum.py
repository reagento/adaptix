import ctypes
import struct
import sys
from dataclasses import dataclass

from adaptix._internal.morphing.native import descriptions

MAX_INLINE_KEY_LENGTH = 32


class EnumHashCache(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("enabled", ctypes.c_uint32)]

    def __init__(self, enum):
        super().__init__()
        self.enum = enum
        self.refresh()

    def refresh(self):
        from adaptix._internal.code_tools.native_access import LOOKUP, get_type_version  # noqa: PLC0415

        hash_method = LOOKUP(self.enum, "__hash__")
        equality = LOOKUP(self.enum, "__eq__")
        self.enabled = (
            any(hash_method is method for method in (object.__hash__, str.__hash__, int.__hash__))
            and any(equality is method for method in (object.__eq__, str.__eq__, int.__eq__))
        )
        self.version = get_type_version(self.enum)


def check_enum_hash(c, enum, generic):

    cache = EnumHashCache(enum)
    c.constants.append(cache)
    guard, learn, checked = c.label("enum_hash_guard"), c.label("enum_hash_learn"), c.label("enum_hash_checked")
    c.asm.label(guard)
    c.load(0, c.constant(enum))
    c.asm.emit(b"\x8b\x88" + struct.pack("<i", c.layout.type_version), "load enum type version")
    c.asm.mov_imm(11, ctypes.addressof(cache))
    c.asm.emit(b"\x41\x3b\x0b", "compare enum hash cache version")
    c.asm.jump(learn, "nz")
    c.asm.emit(b"\x41\x83\x7b\x04\x00", "check builtin enum hash and equality")
    c.asm.jump(generic, "z")
    c.asm.jump(checked)
    c.asm.label(learn)
    c.release(c.call(cache.refresh))
    c.asm.jump(guard)
    c.asm.label(checked)


@dataclass(frozen=True)
class EnumProgram(descriptions.EnumProgram):
    def emit(self, c):
        from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415
        from adaptix._internal.morphing.native.x86_64.union import (  # noqa: PLC0415
            integer_layout_supported,
            match_integer,
        )

        function = descriptions.resolve_function(self.function)
        if not supports_dictionary_cache():
            return c.call(function, c.data)
        generic, done = c.label("enum_slow"), c.label("enum_ready")
        result = c.slot(owned=True)
        if self.loading:
            integer_keys = all(type(key) is int for key, _ in self.mapping)
            if integer_keys and not integer_layout_supported():
                return c.call(function, c.data)
            c.branch_if_type(c.data, int if integer_keys else str, generic, invert=True)
        else:
            c.branch_if_type(c.data, self.enum, generic, invert=True)
            check_enum_hash(c, self.enum, generic)
        for key, value in self.mapping:
            missed = c.label("next_enum_case")
            c.asm.load(0, c.data)
            c.load(11, c.constant(key))
            c.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11")
            matched = c.label("enum_case")
            c.asm.jump(matched, "z")
            if self.loading:
                if integer_keys:
                    match_integer(c, key, missed)
                else:
                    c.match_ascii_key(key, missed)
            else:
                c.asm.jump(missed)
            c.asm.label(matched)
            converted = c.copy_reference(c.constant(value))
            c.transfer(converted, result)
            c.asm.jump(done)
            c.asm.label(missed)
        c.asm.jump(generic)
        return c.fallback_result(result, function, generic, done)


def can_inline_enum(description: descriptions.EnumProgram):
    if (
        sys.implementation.name != "cpython"
        or sys.platform != "linux"
        or sys.maxsize <= (1 << 32)
        or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}
    ):
        return False
    if description.loading:
        return all(
            type(key) is str and key.isascii() and len(key) <= MAX_INLINE_KEY_LENGTH for key, _ in description.mapping
        ) or all(type(key) is int and abs(key) < (1 << 30) for key, _ in description.mapping)
    enum = description.enum
    return any(enum.__hash__ is method for method in (object.__hash__, str.__hash__, int.__hash__)) and any(
        enum.__eq__ is method for method in (object.__eq__, str.__eq__, int.__eq__)
    )
