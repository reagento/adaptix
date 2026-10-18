import ctypes
import struct
import sys
from dataclasses import dataclass
from types import FunctionType
from uuid import UUID, SafeUUID

from adaptix._internal.code_tools.native_dictionary import guard_dictionary_value
from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate
from adaptix._internal.morphing.native import descriptions

HEX_VALUES = ctypes.create_string_buffer(
    bytes(int(chr(value), 16) if chr(value) in "0123456789abcdefABCDEF" else 255 for value in range(256)),
)
HEX_DIGITS = ctypes.create_string_buffer(b"0123456789abcdef")
SEPARATORS = (8, 13, 18, 23)


@dataclass(frozen=True)
class UUIDProgram(descriptions.UUIDProgram):
    def emit(self, c):
        if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
            return c.call(self.function, c.data)
        from adaptix._internal.code_tools.native_access import (  # noqa: PLC0415
            GENERIC_GETTER,
            LOOKUP,
            get_type_version,
            member_offset,
            pointer,
            supports_dictionary_cache,
        )

        if not supports_dictionary_cache():
            return c.call(self.function, c.data)
        initializer = UUID.__init__
        if (
            type(initializer) is not FunctionType
            or UUID.__new__ is not object.__new__ or initializer.__module__ != "uuid"
            or pointer(id(UUID) + c.layout.type_getattro) != GENERIC_GETTER
            or initializer.__code__.co_filename != initializer.__globals__.get("__file__")
            or initializer.__defaults__ != (None,) * 6
            or type(initializer.__kwdefaults__) is not dict
            or initializer.__kwdefaults__.get("is_safe") is not SafeUUID.unknown
            or initializer.__globals__.get("int_") is not int
            or initializer.__globals__.get("object", object) is not object
        ):
            return c.call(self.function, c.data)
        integer_offset = member_offset(LOOKUP(UUID, "int"), UUID.__basicsize__)
        safe_offset = member_offset(LOOKUP(UUID, "is_safe"), UUID.__basicsize__)
        if integer_offset is None or safe_offset is None:
            return c.call(self.function, c.data)
        generic, done = c.label("uuid_slow"), c.label("uuid_done")
        result = c.slot(owned=True)
        c.load(0, c.constant(UUID))
        c.asm.emit(
            b"\x81\xb8" + struct.pack("<iI", c.layout.type_version, get_type_version(UUID)), "check UUID class version",
        )
        c.asm.jump(generic, "nz")
        c.slot()
        last = c.slot()
        buffer = Address(last)
        if self.loading:
            self.constructor_guard(c, initializer, generic)
            c.branch_if_type(c.data, str, generic, invert=True)
            c.asm.load(8, c.data)
            c.asm.emit(b"\x49\x83\x78" + bytes([c.layout.unicode_length]) + b"\x24", "check canonical UUID length")
            c.asm.jump(generic, "nz")
            c.asm.emit(
                b"\x41\x8b\x40" + bytes([c.layout.unicode_state]) + b"\x25\x60\x00\x00\x00\x83\xf8\x60",
                "check compact ASCII UUID",
            )
            c.asm.jump(generic, "nz")
            for position in SEPARATORS:
                c.asm.emit(
                    b"\x41\x80\x78" + bytes([c.layout.unicode_ascii_data + position, 45]), "check UUID separator",
                )
                c.asm.jump(generic, "nz")
            self.parse(c, buffer, generic)
            integer = c.call_c("_PyLong_FromByteArray", buffer, Immediate(16), Immediate(0), Immediate(0))
            created = c.call_c("PyType_GenericAlloc", c.constant(UUID), Immediate(0))
            c.transfer(created, result)
            c.asm.load(0, result)
            c.asm.load(11, integer)
            c.asm.emit(b"\x4c\x89\x58" + bytes([integer_offset]), "steal UUID integer")
            c.asm.clear(integer)
            safe = c.new_reference(SafeUUID.unknown)
            c.asm.load(0, result)
            c.asm.load(11, safe)
            c.asm.emit(b"\x4c\x89\x58" + bytes([safe_offset]), "steal UUID safety flag")
            c.asm.clear(safe)
        else:
            self.format(c, buffer, integer_offset, result, generic)
        c.asm.jump(done)
        return c.fallback_result(result, self.function, generic, done)

    def constructor_guard(self, c, initializer, generic):
        c.load(0, c.constant(initializer))
        for offset, value in (
            (c.layout.function_code, initializer.__code__),
            (c.layout.function_defaults, initializer.__defaults__),
            (c.layout.function_kwdefaults, initializer.__kwdefaults__),
        ):
            c.load(11, c.constant(value))
            c.asm.emit(b"\x4c\x39\x58" + bytes([offset]), "check UUID initializer metadata")
            c.asm.jump(generic, "nz")
        missing = object()
        for namespace, key, expected in (
            (initializer.__globals__, "int_", int),
            (initializer.__globals__, "object", initializer.__globals__.get("object", missing)),
            (initializer.__builtins__, "object", object),
            (initializer.__kwdefaults__, "is_safe", SafeUUID.unknown),
        ):
            guard_dictionary_value(c, namespace, key, expected, missing, generic)

    def parse(self, c, buffer, generic):
        c.constants.append(HEX_VALUES)
        c.asm.mov_imm(11, ctypes.addressof(HEX_VALUES))
        positions = [position for position in range(36) if position not in SEPARATORS]
        c.asm.lea(9, buffer.slot)
        for index in range(16):
            for register, position in ((0, positions[index * 2]), (1, positions[index * 2 + 1])):
                c.asm.emit(
                    b"\x41\x0f\xb6" + bytes([0x40 if register == 0 else 0x48, c.layout.unicode_ascii_data + position]),
                    "load UUID hex character",
                )
                c.asm.emit(
                    b"\x41\x0f\xb6" + (b"\x04\x03" if register == 0 else b"\x0c\x0b"), "decode UUID nibble",
                )
                c.asm.emit(b"\x83" + bytes([0xF8 if register == 0 else 0xF9, 15]), "validate UUID hex character")
                c.asm.jump(generic, "a")
            c.asm.emit(b"\xc1\xe0\x04\x09\xc8\x41\x88\x41" + bytes([index]), "store UUID byte")

    def format(self, c, buffer, integer_offset, result, generic):
        hexadecimal = UUID.hex
        if type(hexadecimal) is not property:
            c.asm.jump(generic)
            return
        for function in (self.function, hexadecimal.fget):
            if (
                type(function) is not FunctionType
                or function.__code__.co_filename != UUID.__init__.__globals__.get("__file__")
            ):
                c.asm.jump(generic)
                return
            c.load(0, c.constant(function))
            c.load(11, c.constant(function.__code__))
            c.asm.emit(b"\x4c\x39\x58" + bytes([c.layout.function_code]), "check UUID formatter code")
            c.asm.jump(generic, "nz")
        c.branch_if_type(c.data, UUID, generic, invert=True)
        c.asm.load(0, c.data)
        c.asm.emit(b"\x48\x8b\x40" + bytes([integer_offset]), "load UUID integer")
        c.asm.test_jump(0, generic)
        integer = c.copy_loaded_reference()
        c.branch_if_type(integer, int, generic, invert=True)
        overflow, encoded = c.label("uuid_integer_overflow"), c.label("uuid_integer_encoded")
        c.call_c(
            "_PyLong_AsByteArray", integer, buffer, Immediate(16), Immediate(0), Immediate(0), Immediate(1),
            result="int", error_label=overflow,
        )
        c.release(integer)
        c.asm.jump(encoded)
        c.asm.label(overflow)
        c.call_c("PyErr_Clear", result="void")
        c.release(integer)
        c.asm.jump(generic)
        c.asm.label(encoded)
        text = c.call_c("PyUnicode_New", Immediate(36), Immediate(127))
        c.transfer(text, result)
        c.asm.load(9, result)
        c.asm.lea(8, buffer.slot)
        c.constants.append(HEX_DIGITS)
        c.asm.mov_imm(11, ctypes.addressof(HEX_DIGITS))
        positions = [position for position in range(36) if position not in SEPARATORS]
        for index in range(16):
            c.asm.emit(b"\x41\x0f\xb6\x40" + bytes([index]), "load UUID byte")
            c.asm.emit(b"\x89\xc1\xc1\xe9\x04\x83\xe0\x0f", "extract UUID nibbles")
            c.asm.emit(b"\x41\x0f\xb6\x0c\x0b\x41\x0f\xb6\x04\x03", "encode UUID hex characters")
            c.asm.emit(
                b"\x41\x88\x49" + bytes([c.layout.unicode_ascii_data + positions[index * 2]]),
                "store first UUID hex digit",
            )
            c.asm.emit(
                b"\x41\x88\x41" + bytes([c.layout.unicode_ascii_data + positions[index * 2 + 1]]),
                "store second UUID hex digit",
            )
        for position in SEPARATORS:
            c.asm.emit(b"\x41\xc6\x41" + bytes([c.layout.unicode_ascii_data + position, 45]), "store UUID separator")
