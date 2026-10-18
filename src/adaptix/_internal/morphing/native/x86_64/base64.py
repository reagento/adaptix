# ruff: noqa: PLR2004
import ctypes
import sys
from dataclasses import dataclass
from functools import cache

from adaptix._internal.code_tools.cpython_layout.selection import get_cpython_layout
from adaptix._internal.code_tools.x86_64_assembler import Immediate
from adaptix._internal.morphing.native import descriptions

LAYOUT = get_cpython_layout()

ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
ENCODE = ctypes.create_string_buffer(ALPHABET)
DECODE = ctypes.create_string_buffer(bytes(ALPHABET.find(bytes([index])) & 255 for index in range(256)))


@cache
def supported():
    if LAYOUT is None or sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        return False
    from adaptix._internal.code_tools.native_access import supports_dictionary_cache  # noqa: PLC0415

    probe = bytes(bytearray(b"abc"))
    return supports_dictionary_cache() and ctypes.string_at(id(probe) + LAYOUT.bytes_data, 4) == b"abc\0"


def decode_group(c, count, generic):
    c.asm.emit(b"\x45\x31\xd2", "clear base64 group")
    for index in range(count):
        c.asm.emit(b"\x41\x0f\xb6\x40" + bytes([index]), "read encoded character")
        c.asm.emit(b"\x41\x0f\xb6\x04\x03\x83\xf8\x3f", "decode character; reject non-alphabet")
        c.asm.jump(generic, "a")
        c.asm.emit(b"\x41\xc1\xe2\x06\x41\x09\xc2", "append six decoded bits")
    # Align the decoded group as a 24-bit value, also for padded final groups.
    if count < 4:
        c.asm.emit(b"\x41\xc1\xe2" + bytes([(4 - count) * 6]), "align padded base64 group")
    for index in range(count - 1):
        c.asm.emit(b"\x44\x89\xd0", "mov eax, r10d")
        if index < 2:
            c.asm.emit(b"\xc1\xe8" + bytes([16 - index * 8]), "select decoded byte")
        c.asm.emit(b"\x41\x88\x41" + bytes([index]), "store decoded byte")


def load(c, function):  # noqa: PLR0915
    generic, done, empty = c.label("base64_slow"), c.label("base64_done"), c.label("base64_empty")
    result = c.slot(owned=True)
    length, groups, padding = c.slot(), c.slot(), c.slot()
    c.branch_if_type(c.data, str, generic, invert=True)
    c.asm.load(8, c.data)
    c.asm.emit(b"\x41\x8b\x40" + bytes([c.layout.unicode_state]) + b"\x83\xe0\x60\x83\xf8\x60", "check compact ASCII")
    c.asm.jump(generic, "nz")
    c.asm.emit(b"\x49\x8b\x40" + bytes([c.layout.unicode_length]) + b"\x48\x85\xc0", "read encoded length")
    c.asm.jump(empty, "z")
    c.asm.emit(b"\xa8\x03", "check complete base64 groups")
    c.asm.jump(generic, "nz")
    c.asm.emit(b"\x31\xc9", "clear padding count")
    no_pad, one_pad = c.label("base64_no_padding"), c.label("base64_one_padding")
    c.asm.emit(b"\x41\x80\x7c\x00" + bytes([c.layout.unicode_ascii_data-1]) + b"\x3d", "check final padding character")
    c.asm.jump(no_pad, "nz")
    c.asm.emit(
        b"\xff\xc1\x41\x80\x7c\x00" + bytes([c.layout.unicode_ascii_data - 2]) + b"\x3d",
        "check second padding character",
    )
    c.asm.jump(one_pad, "nz")
    c.asm.emit(b"\xff\xc1", "increment padding count")
    c.asm.label(one_pad)
    c.asm.label(no_pad)
    c.asm.store(padding, 1)
    c.asm.emit(b"\x48\xc1\xe8\x02", "divide encoded length by four")
    c.asm.store(groups)
    c.asm.emit(b"\x48\x8d\x04\x40\x48\x29\xc8", "decoded length = groups * 3 - padding")
    c.asm.store(length)
    value = c.call_c("PyBytes_FromStringAndSize", Immediate(0), length)
    c.transfer(value, result)
    c.asm.load(8, c.data)
    c.asm.emit(b"\x49\x83\xc0" + bytes([c.layout.unicode_ascii_data]), "point at ASCII payload")
    c.asm.load(9, result)
    c.asm.emit(b"\x49\x83\xc1" + bytes([c.layout.bytes_data]), "point at bytes payload")
    c.constants.append(DECODE)
    c.asm.mov_imm(11, ctypes.addressof(DECODE))
    c.asm.load(1, groups)
    c.asm.emit(b"\x48\xff\xc9", "leave final group for padding handling")
    final = c.label("base64_final_group")
    c.asm.jump(final, "z")
    loop = c.label("base64_decode_loop")
    c.asm.label(loop)
    decode_group(c, 4, generic)
    c.asm.emit(b"\x49\x83\xc0\x04\x49\x83\xc1\x03\x48\xff\xc9", "advance base64 source and destination")
    c.asm.jump(loop, "nz")
    c.asm.label(final)
    c.asm.load(0, padding)
    for pad in (0, 1, 2):
        next_pad = c.label("base64_next_padding")
        c.asm.emit(b"\x83\xf8" + bytes([pad]), "check final padding count")
        c.asm.jump(next_pad, "nz")
        decode_group(c, 4 - pad, generic)
        c.asm.jump(done)
        c.asm.label(next_pad)
    c.asm.label(empty)
    value = c.call_c("PyBytes_FromStringAndSize", Immediate(0), Immediate(0))
    c.transfer(value, result)
    c.asm.jump(done)
    return c.fallback_result(result, function, generic, done, cleanup=(result,))


def encode_group(c, count):
    c.asm.emit(b"\x45\x31\xd2", "clear binary group")
    for index in range(count):
        c.asm.emit(b"\x41\x0f\xb6\x40" + bytes([index]), "read source byte")
        c.asm.emit(b"\x41\xc1\xe2\x08\x41\x09\xc2", "append binary byte")
    if count < 3:
        c.asm.emit(b"\x41\xc1\xe2" + bytes([(3 - count) * 8]), "align final binary group")
    for index in range(4):
        if index > count:
            c.asm.emit(b"\x41\xc6\x41" + bytes([index, 61]), "store base64 padding")
            continue
        c.asm.emit(b"\x44\x89\xd0", "mov eax, r10d")
        if index < 3:
            c.asm.emit(b"\xc1\xe8" + bytes([18 - index * 6]), "select six source bits")
        c.asm.emit(b"\x83\xe0\x3f\x41\x0f\xb6\x04\x03", "read base64 alphabet")
        c.asm.emit(b"\x41\x88\x41" + bytes([index]), "store base64 character")


def dump(c, function):  # noqa: PLR0915
    generic, done = c.label("base64_dump_slow"), c.label("base64_dump_done")
    result = c.slot(owned=True)
    c.branch_if_type(c.data, bytes, generic, invert=True)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.var_size]), "read bytes length")
    groups, remainder, length = c.slot(), c.slot(), c.slot()
    c.asm.emit(b"\x31\xd2\xb9\x03\x00\x00\x00\x48\xf7\xf1", "divide binary length by three")
    c.asm.store(groups)
    c.asm.store(remainder, 2)
    c.asm.emit(b"\x48\x85\xd2", "check final incomplete group")
    full = c.label("base64_encoded_length")
    c.asm.jump(full, "z")
    c.asm.emit(b"\x48\xff\xc0", "add final encoded group")
    c.asm.label(full)
    # Python bytes cannot approach this limit without exhausting address space.
    # The arithmetic guard nevertheless retains the standard overflow behavior.
    c.asm.mov_imm(11, ((1 << 63) - c.layout.unicode_ascii_data - 2) // 4)
    c.asm.emit(b"\x4c\x39\xd8", "check encoded allocation size")
    c.asm.jump(generic, "a")
    c.asm.emit(b"\x48\xc1\xe0\x02", "encoded length = groups * 4")
    c.asm.store(length)
    c.asm.emit(b"\x48\x83\xc0" + bytes([c.layout.unicode_ascii_data + 1]), "add compact ASCII header and terminator")
    allocation_size = c.slot()
    c.asm.store(allocation_size)
    allocation = c.call_c("PyObject_Malloc", allocation_size, result="pointer")
    no_memory = c.label("base64_no_memory")
    c.branch_if_null(allocation, no_memory)
    c.asm.load(9, allocation)
    c.asm.emit_memory(
        b"\x49\xc7", 0x01, c.layout.object_refcount, "initialize string reference count", immediate=b"\x01\x00\x00\x00",
    )
    c.load(0, c.constant(str))
    c.asm.emit(b"\x49\x89\x41" + bytes([c.layout.object_type]), "initialize string type")
    c.asm.load(0, length)
    c.asm.emit((
                   b"\x49\x89\x41"
                   + bytes([c.layout.unicode_length])
                   + b"\x49\xc7\x41"
                   + bytes([c.layout.unicode_hash])
                   + b"\xff\xff\xff\xff"
               ), "initialize string length and hash")
    c.asm.emit(
        (
            b"\x49\xc7\x41"
            + bytes([c.layout.unicode_state])
            + b"\x64\x00\x00\x00\x41\xc6\x44\x01"
            + bytes([c.layout.unicode_ascii_data])
            + b"\x00"
        ), "initialize compact ASCII flags and terminator",
    )
    c.asm.store(result, 9)
    c.asm.emit(b"\x49\x83\xc1" + bytes([c.layout.unicode_ascii_data]), "point at ASCII output payload")
    c.asm.load(8, c.data)
    c.asm.emit(b"\x49\x83\xc0" + bytes([c.layout.bytes_data]), "point at bytes input payload")
    c.constants.append(ENCODE)
    c.asm.mov_imm(11, ctypes.addressof(ENCODE))
    c.asm.load(1, groups)
    c.asm.emit(b"\x48\x85\xc9", "check full input groups")
    final = c.label("base64_encode_final")
    c.asm.jump(final, "z")
    loop = c.label("base64_encode_loop")
    c.asm.label(loop)
    encode_group(c, 3)
    c.asm.emit(b"\x49\x83\xc0\x03\x49\x83\xc1\x04\x48\xff\xc9", "advance base64 input and output")
    c.asm.jump(loop, "nz")
    c.asm.label(final)
    c.asm.load(0, remainder)
    c.asm.test_jump(0, done, bits=32)
    two = c.label("base64_two_final_bytes")
    c.asm.emit(b"\x83\xf8\x02", "check two final bytes")
    c.asm.jump(two, "z")
    encode_group(c, 1)
    c.asm.jump(done)
    c.asm.label(two)
    encode_group(c, 2)
    c.asm.jump(done)
    c.asm.label(no_memory)
    c.call_c("PyErr_NoMemory")
    return c.fallback_result(result, function, generic, done)


@dataclass(frozen=True)
class Base64Program(descriptions.Base64Program):
    def emit(self, c):
        function = descriptions.resolve_function(self.function)
        if not c.has_validated_object_header or not supported():
            return c.call(function, c.data)
        return load(c, function) if self.loading else dump(c, function)
