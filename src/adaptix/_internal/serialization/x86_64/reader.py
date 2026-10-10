import ctypes
import json
import struct
from collections.abc import Callable

from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
from adaptix._internal.serialization.perfect_hash import HASH_PRIME, PerfectHash
from adaptix._internal.serialization.x86_64.common import NATIVE_STACK_BUDGET, JsonEmitter, c_address

CURSOR = 0
END = 8
KEY_MODE = 16
ROUTINE = 24
STACK_FLOOR = 32
KEY_INDEX = 40


class JsonCursor(JsonEmitter):
    def peek(self, exhausted: str):
        self.asm.emit(b"\x4d\x39\xec", "cmp r12, r13")
        self.asm.jump(exhausted, "ae")
        self.asm.emit(b"\x41\x0f\xb6\x04\x24", "movzx eax, byte [r12]")

    def advance(self):
        self.asm.emit(b"\x49\xff\xc4", "inc r12")

    def compare(self, byte: int, label: str, condition: str = "z"):
        self.asm.emit(b"\x83\xf8" + bytes([byte]), f"cmp eax, {byte}")
        self.asm.jump(label, condition)

    def whitespace(self):
        loop, step, done = (self.compiler.label(name) for name in ("space_loop", "space_step", "space_done"))
        self.asm.label(loop)
        self.peek(done)
        for byte in b" \t\n\r":
            self.compare(byte, step)
        self.asm.jump(done)
        self.asm.label(step)
        self.advance()
        self.asm.jump(loop)
        self.asm.label(done)


class JsonReader(JsonCursor):
    def __init__(self, compiler: X86Compiler, decode_scalar: Callable, table: PerfectHash | None, *, key_index=False):
        super().__init__(compiler)
        self.decode_scalar = decode_scalar
        self.table = table
        self.key_index = key_index
        self.result = compiler.slot(owned=True)
        self.done = compiler.label("value_done")
        self.invalid = compiler.label("invalid_value")
        self.container_error = compiler.label("container_error")
        self.container_invalid = compiler.label("invalid_container")
        self.container_done = compiler.label("container_done")

    def return_value(self, value):
        self.compiler.transfer(value, self.result)
        self.asm.jump(self.done)

    def emit(self):
        c = self.compiler
        c.reserve_loop_registers()
        self.stack_guard(STACK_FLOOR, self.invalid)
        self.state_load(CURSOR, 12)
        self.state_load(END, 13)
        self.whitespace()
        self.peek(self.invalid)
        labels = {byte: c.label(name) for byte, name in ((34, "string"), (91, "array"), (123, "object"))}
        for byte, label in labels.items():
            self.compare(byte, label)
        literal_labels = [
            (b"true", True, c.label("true")),
            (b"false", False, c.label("false")),
            (b"null", None, c.label("null")),
        ]
        for token, _, label in literal_labels:
            self.compare(token[0], label)
        number = c.label("number")
        self.compare(45, number)
        self.compare(48, self.invalid, "b")
        self.compare(57, self.invalid, "a")
        self.asm.jump(number)
        self.asm.label(labels[34])
        self.string()
        self.asm.label(number)
        self.number()
        for token, value, label in literal_labels:
            self.asm.label(label)
            length = c.slot()
            self.asm.emit(b"\x4c\x89\xe8\x4c\x29\xe0", "mov rax, r13; sub rax, r12")
            self.asm.store(length)
            self.asm.emit(b"\x48\x83\xf8" + bytes([len(token)]), f"cmp rax, {len(token)}")
            self.asm.jump(self.invalid, "b")
            start = c.slot()
            self.asm.store(start, 12)
            c.call_c(c_address("memcmp"), start, self.literal(token), Immediate(len(token)), result="pointer")
            self.asm.test_jump(0, self.invalid, "nz", bits=32)
            self.asm.emit(b"\x49\x83\xc4" + bytes([len(token)]), f"add r12, {len(token)}")
            self.return_value(c.new_reference(value))
        for is_object, label in ((False, labels[91]), (True, labels[123])):
            self.asm.label(label)
            self.container(is_object=is_object)
        self.asm.label(self.container_invalid)
        self.fail(self.container_error)
        self.asm.label(self.container_error)
        c.call_c("Py_LeaveRecursiveCall", result="void")
        self.asm.jump("error")
        self.asm.label(self.container_done)
        c.call_c("Py_LeaveRecursiveCall", result="void")
        self.asm.jump(self.done)
        self.asm.label(self.invalid)
        self.fail("error")
        self.asm.label(self.done)
        self.state_store(CURSOR, 12)
        c.call_error_label = "error"
        return c.finish(self.result)

    def string(self):  # noqa: PLR0915
        c = self.compiler
        token, start, length = c.slot(), c.slot(), c.slot()
        self.asm.store(token, 12)
        self.advance()
        self.asm.store(start, 12)
        loop, close, escaped, escaped_loop = (
            c.label(name) for name in ("string_loop", "string_end", "escape", "escaped_loop")
        )
        self.string_vectors()
        self.asm.label(loop)
        self.string_chunk(loop, c.label("string_tail"), reader=True)
        self.peek(self.invalid)
        self.compare(34, close)
        self.compare(92, escaped)
        self.compare(32, self.invalid, "b")
        self.advance()
        self.asm.jump(loop)
        self.asm.label(close)
        self.asm.emit(b"\x4c\x89\xe0", "mov rax, r12")
        self.asm.load(2, start)
        self.asm.emit(b"\x48\x29\xd0", "sub rax, rdx")
        self.asm.store(length)
        generic = c.label("decode_key")
        if self.table is not None:
            self.state_load(KEY_MODE)
            self.asm.test_jump(0, generic)
            self.hash_lookup(start, length, generic)
        self.asm.label(generic)
        value = c.call_c("PyUnicode_DecodeUTF8", start, length, Immediate(0))
        self.advance()
        self.return_value(value)
        self.asm.label(escaped)
        self.advance()
        self.peek(self.invalid)
        self.advance()
        self.asm.label(escaped_loop)
        self.string_chunk(escaped_loop, c.label("escape_tail"), reader=True)
        self.peek(self.invalid)
        escaped_close = c.label("escaped_end")
        self.compare(34, escaped_close)
        self.compare(92, escaped)
        self.compare(32, self.invalid, "b")
        self.advance()
        self.asm.jump(escaped_loop)
        self.asm.label(escaped_close)
        self.advance()
        self.asm.emit(b"\x4c\x89\xe0", "mov rax, r12")
        self.asm.load(2, token)
        self.asm.emit(b"\x48\x29\xd0", "sub rax, rdx")
        self.asm.store(length)
        self.simple_escapes(start, length)
        text = c.call_c("PyUnicode_DecodeUTF8", token, length, Immediate(0))
        parsed = c.call(json.decoder.scanstring, text, c.constant(1))
        c.call_c("PyTuple_GetItem", parsed, Immediate(0), result="pointer")
        value = c.copy_loaded_reference()
        c.release(parsed)
        c.release(text)
        self.return_value(value)

    def simple_escapes(self, start, token_length):
        c = self.compiler
        length = c.slot()
        self.asm.load(0, token_length)
        self.asm.emit(b"\x48\x83\xe8\x02", "sub rax, 2  # omit quotes")
        self.asm.store(length)
        buffer = c.call_c("PyBytes_FromStringAndSize", Immediate(0), length)
        pointer = c.call_c("PyBytes_AsString", buffer, result="pointer")
        self.asm.load(8, pointer)
        self.asm.load(2, start)
        self.asm.load(1, length)
        self.asm.emit(b"\x48\x01\xd1", "add rcx, rdx")
        loop, escape, close, generic = (
            c.label(name) for name in ("unescape_loop", "unescape_byte", "unescape_end", "unicode_escape")
        )
        translations = bytearray(256)
        for source, target in ((34, 34), (92, 92), (47, 47), (98, 8), (102, 12), (110, 10), (114, 13), (116, 9)):
            translations[source] = target
        translation = self.literal(bytes(translations))
        self.string_vectors()
        self.asm.label(loop)
        self.string_chunk(loop, c.label("unescape_tail"), reader=False, copy=True)
        self.asm.emit(b"\x48\x39\xca", "cmp rdx, rcx")
        self.asm.jump(close, "ae")
        self.asm.emit(b"\x0f\xb6\x02", "movzx eax, byte [rdx]")
        self.asm.emit(b"\x83\xf8\x5c", "cmp eax, 92")
        self.asm.jump(escape, "z")
        self.asm.emit(b"\x41\x88\x00\x49\xff\xc0\x48\xff\xc2", "mov [r8], al; inc r8; inc rdx")
        self.asm.jump(loop)
        self.asm.label(escape)
        self.asm.emit(b"\x48\xff\xc2\x48\x39\xca", "inc rdx; cmp rdx, rcx")
        self.asm.jump(generic, "ae")
        self.asm.emit(b"\x0f\xb6\x02", "movzx eax, byte [rdx]")
        c.load(11, translation)
        self.asm.emit(b"\x41\x0f\xb6\x04\x03", "movzx eax, byte [r11+rax]")
        self.asm.test_jump(0, generic, bits=32)
        self.asm.emit(b"\x41\x88\x00\x49\xff\xc0\x48\xff\xc2", "mov [r8], al; inc r8; inc rdx")
        self.asm.jump(loop)
        self.asm.label(close)
        self.asm.load(0, pointer)
        self.asm.emit(b"\x49\x29\xc0", "sub r8, rax")
        written = c.slot()
        self.asm.store(written, 8)
        decoded = c.call_c("PyUnicode_DecodeUTF8", pointer, written, Immediate(0))
        c.release(buffer)
        self.return_value(decoded)
        self.asm.label(generic)
        c.release(buffer)

    def hash_lookup(self, start, length, generic):  # noqa: PLR0915
        c, table = self.compiler, self.table
        displacements = (ctypes.c_int32 * len(table.displacements))(*table.displacements)
        buffers = [ctypes.create_string_buffer(value) if value is not None else None for value in table.entries]
        # Each native entry contains length, UTF-8 pointer and PyObject pointer.
        fields = []
        indices = {name: index for index, name in enumerate(name for name in table.names if name is not None)}
        for value, buffer, name in zip(table.entries, buffers, table.names, strict=True):
            fields.extend((len(value), ctypes.addressof(buffer), id(name)) if value is not None else (0, 0, 0))
            if self.key_index:
                fields.append(indices.get(name, 0))
        entries = (ctypes.c_uint64 * len(fields))(*fields)
        c.constants.extend((table, displacements, entries, *buffers))
        loop, hashed, singleton, selected = (c.label(name) for name in ("hash_loop", "hashed", "singleton", "selected"))
        self.asm.mov_imm(0, table.seed)
        self.asm.load(2, start)
        self.asm.label(loop)
        self.asm.emit(b"\x4c\x39\xe2", "cmp rdx, r12")
        self.asm.jump(hashed, "ae")
        self.asm.emit(b"\x0f\xb6\x0a\x31\xc8", "movzx ecx, byte [rdx]; xor eax, ecx")
        self.asm.emit(b"\x69\xc0" + struct.pack("<I", HASH_PRIME), f"imul eax, eax, {HASH_PRIME}")
        self.asm.emit(b"\x48\xff\xc2", "inc rdx")
        self.asm.jump(loop)
        self.asm.label(hashed)
        self.asm.emit(
            b"\x89\xc1\x81\xe1" + struct.pack("<I", len(table.displacements) - 1), "mov ecx, eax; and ecx, bucket_mask",
        )
        self.asm.mov_imm(11, ctypes.addressof(displacements))
        self.asm.emit(b"\x41\x8b\x0c\x8b", "mov ecx, [r11+rcx*4]")
        self.asm.test_jump(1, generic, bits=32)
        self.asm.jump(singleton, "s")
        self.asm.emit(
            b"\x0f\xaf\xc1\xc1\xe8\x10\x25" + struct.pack("<I", len(table.entries) - 1),
            "imul eax, ecx; shr eax, 16; and eax, slot_mask",
        )
        self.asm.jump(selected)
        self.asm.label(singleton)
        self.asm.emit(b"\x89\xc8\xf7\xd8\xff\xc8", "mov eax, ecx; neg eax; dec eax")
        self.asm.label(selected)
        entry_size = 32 if self.key_index else 24
        self.asm.emit(b"\x48\x6b\xc0" + bytes([entry_size]), f"imul rax, rax, {entry_size}")
        self.asm.mov_imm(11, ctypes.addressof(entries))
        self.asm.emit(b"\x4c\x01\xd8", "add rax, r11")
        entry = c.slot()
        self.asm.store(entry)
        self.asm.load(2, length)
        self.asm.emit(b"\x48\x39\x10", "cmp [rax], rdx")
        self.asm.jump(generic, "nz")
        self.asm.emit(b"\x48\x8b\x70\x08", "mov rsi, [rax+8]")
        self.asm.test_jump(6, generic)
        address = c.slot()
        self.asm.store(address, 6)
        c.call_c(c_address("memcmp"), start, address, length, result="pointer")
        self.asm.test_jump(0, generic, "nz", bits=32)
        self.asm.load(0, entry)
        if self.key_index:
            self.asm.emit(b"\x48\x8b\x50\x18", "mov rdx, [rax+24]  # schema key index")
            self.state_store(KEY_INDEX, 2)
        self.asm.emit(b"\x48\x8b\x40\x10", "mov rax, [rax+16]")
        value = c.copy_loaded_reference()
        self.advance()
        self.return_value(value)

    def scalar_token(self, start):
        c = self.compiler
        length = c.slot()
        self.asm.emit(b"\x4c\x89\xe0", "mov rax, r12")
        self.asm.load(2, start)
        self.asm.emit(b"\x48\x29\xd0", "sub rax, rdx")
        self.asm.store(length)
        token = c.call_c("PyBytes_FromStringAndSize", start, length)
        value = c.call(self.decode_scalar, token)
        c.release(token)
        self.return_value(value)

    def number(self):  # noqa: PLR0915
        c = self.compiler
        start, number = c.slot(), c.slot()
        self.asm.store(start, 12)
        positive, zero, digits, finish, slow, scan = (
            c.label(name) for name in ("positive", "zero", "digits", "integer_end", "scalar_slow", "scan_scalar")
        )
        self.asm.emit(b"\x45\x31\xf6\x45\x31\xff", "xor r14d, r14d; xor r15d, r15d")
        self.compare(45, positive, "nz")
        self.asm.emit(b"\x41\xbf\x01\x00\x00\x00", "mov r15d, 1")
        self.advance()
        self.peek(self.invalid)
        self.asm.label(positive)
        self.compare(48, self.invalid, "b")
        self.compare(57, self.invalid, "a")
        self.compare(48, zero)
        self.asm.label(digits)
        self.asm.emit(b"\x83\xe8\x30", "sub eax, 48")
        self.asm.emit(b"\x4d\x6b\xf6\x0a", "imul r14, r14, 10")
        self.asm.jump(slow, "o")
        self.asm.emit(b"\x49\x01\xc6", "add r14, rax")
        self.asm.jump(slow, "o")
        self.advance()
        self.peek(finish)
        self.compare(48, finish, "b")
        self.compare(57, finish, "a")
        self.asm.jump(digits)
        self.asm.label(zero)
        self.advance()
        self.peek(finish)
        self.compare(48, finish, "b")
        self.compare(57, self.invalid, "be")
        self.asm.label(finish)
        # r12 may equal end; never dereference it here.
        self.asm.emit(b"\x4d\x39\xec", "cmp r12, r13")
        integer = c.label("integer")
        self.asm.jump(integer, "ae")
        self.asm.emit(b"\x41\x0f\xb6\x04\x24", "movzx eax, byte [r12]")
        floating = c.label("floating")
        for byte in b".eE":
            self.compare(byte, floating)
        self.asm.label(integer)
        self.asm.emit(b"\x4c\x89\xf0", "mov rax, r14")
        signed = c.label("signed")
        self.asm.test_jump(15, signed)
        self.asm.emit(b"\x48\xf7\xd8", "neg rax")
        self.asm.label(signed)
        self.asm.store(number)
        self.return_value(c.call_c("PyLong_FromLongLong", number))
        self.asm.label(floating)
        self.floating(start)
        self.asm.label(slow)
        self.asm.label(scan)
        end = c.label("scalar_end")
        self.peek(end)
        for byte in b" \t\n\r,]}":
            self.compare(byte, end)
        self.advance()
        self.asm.jump(scan)
        self.asm.label(end)
        self.scalar_token(start)

    def digit_sequence(self):
        c = self.compiler
        loop, end = c.label("float_digits"), c.label("float_digits_end")
        self.peek(self.invalid)
        self.compare(48, self.invalid, "b")
        self.compare(57, self.invalid, "a")
        self.asm.label(loop)
        self.advance()
        self.peek(end)
        self.compare(48, end, "b")
        self.compare(57, loop, "be")
        self.asm.label(end)

    def floating(self, start):
        c = self.compiler
        exponent, exponent_digits, end = (c.label(name) for name in ("exponent", "exponent_digits", "float_end"))
        self.compare(46, exponent, "nz")
        self.advance()
        self.digit_sequence()
        self.peek(end)
        self.asm.label(exponent)
        self.compare(101, exponent_digits)
        self.compare(69, end, "nz")
        self.asm.label(exponent_digits)
        self.advance()
        self.peek(self.invalid)
        signed = c.label("exponent_signed")
        self.compare(43, signed)
        unsigned = c.label("exponent_unsigned")
        self.compare(45, unsigned, "nz")
        self.asm.label(signed)
        self.advance()
        self.asm.label(unsigned)
        self.digit_sequence()
        self.asm.label(end)
        parsed_end = c.slot()
        c.call_c("PyOS_string_to_double", start, Address(parsed_end), Immediate(0), result="pointer")
        self.asm.load(0, parsed_end)
        self.asm.emit(b"\x4c\x39\xe0", "cmp rax, r12")
        self.asm.jump(self.invalid, "nz")
        number = c.slot()
        self.asm.emit(b"\x66\x48\x0f\x7e\xc0", "movq rax, xmm0")
        self.asm.store(number)
        c.call_c("PyErr_Occurred", result="pointer")
        self.asm.test_jump(0, c.call_error_label, "nz")
        self.asm.load(0, number)
        self.asm.emit(b"\x66\x48\x0f\x6e\xc0", "movq xmm0, rax")
        value = c.call_c("PyFloat_FromDouble")
        self.return_value(value)

    def read_child(self, *, key: bool = False):
        c = self.compiler
        self.state_store(CURSOR, 12)
        self.asm.mov_imm(0, int(key))
        self.state_store(KEY_MODE)
        self.state_load(ROUTINE)
        address = c.slot()
        self.asm.store(address)
        value = c.call_c(address, c.data)
        self.state_load(CURSOR, 12)
        return value

    def container(self, *, is_object: bool):
        c = self.compiler
        c.call_c("Py_EnterRecursiveCall", self.literal(b" while decoding JSON"), result="pointer")
        self.asm.test_jump(0, "error", "nz", bits=32)
        c.call_error_label = self.container_error
        container = c.call_c("PyDict_New") if is_object else c.call_c("PyList_New", Immediate(0))
        loop, close = c.label("items"), c.label("container_end")
        self.advance()
        self.whitespace()
        self.peek(self.container_invalid)
        self.compare(125 if is_object else 93, close)
        self.asm.label(loop)
        if is_object:
            self.peek(self.container_invalid)
            self.compare(34, self.container_invalid, "nz")
            key = self.read_child(key=True)
            self.whitespace()
            self.peek(self.container_invalid)
            self.compare(58, self.container_invalid, "nz")
            self.advance()
            value = self.read_child()
            c.call_c("PyDict_SetItem", container, key, value, result="int")
            c.release(key)
        else:
            value = self.read_child()
            c.call_c("PyList_Append", container, value, result="int")
        c.release(value)
        self.whitespace()
        self.peek(self.container_invalid)
        self.compare(125 if is_object else 93, close)
        self.compare(44, self.container_invalid, "nz")
        self.advance()
        self.whitespace()
        self.peek(self.container_invalid)
        self.compare(125 if is_object else 93, self.container_invalid)
        self.asm.jump(loop)
        self.asm.label(close)
        self.advance()
        c.transfer(container, self.result)
        self.asm.jump(self.container_done)
        c.call_error_label = "error"


def make_decoder(compiler_factory, decode_fallback, table, *, model=None, decode_scalar=None):  # noqa: PLR0915
    routine = JsonReader(
        compiler_factory("json_read_value"), decode_fallback if decode_scalar is None else decode_scalar, table,
        key_index=model is not None,
    ).emit()
    c = compiler_factory("json_decode")
    c.constants.append(routine)
    c.reserve_loop_registers()
    slots = [c.slot() for _ in range(5 if model is None else 6)][::-1]
    cursor, end, key_mode, address, floor = slots[:5]
    result = c.slot(owned=True)
    bytes_input, str_input, bytearray_input, ready, failure, fallback, done = (
        c.label(name) for name in ("bytes", "str", "bytearray", "ready", "decode_failure", "fallback", "decode_done")
    )
    c.call_error_label = failure
    if c.has_validated_object_header:
        for tp, label in ((bytes, bytes_input), (str, str_input), (bytearray, bytearray_input)):
            c.branch_if_type(c.data, tp, label)
    c.asm.jump(fallback)
    c.asm.label(bytearray_input)
    copied = c.call_c("PyBytes_FromObject", c.data)
    source = copied
    c.asm.jump(ready)
    c.asm.label(bytes_input)
    source_bytes = c.slot()
    c.asm.load(0, c.data)
    c.asm.store(source_bytes)
    c.asm.jump(ready + "_bytes")
    c.asm.label(ready)
    c.asm.load(0, source)
    c.asm.store(source_bytes)
    c.asm.label(ready + "_bytes")
    pointer = c.call_c("PyBytes_AsString", source_bytes, result="pointer")
    size = c.call_c("PyBytes_Size", source_bytes, result="pointer")
    c.asm.load(12, pointer)
    c.asm.load(13, size)
    c.asm.emit(b"\x4d\x01\xe5", "add r13, r12")
    c.asm.jump(ready + "_input")
    c.asm.label(str_input)
    size_str = c.slot()
    c.call_c("PyUnicode_AsUTF8AndSize", c.data, Address(size_str), result="pointer")
    c.asm.test_jump(0, failure)
    c.asm.store(cursor)
    c.asm.load(12, cursor)
    c.asm.load(13, size_str)
    c.asm.emit(b"\x4d\x01\xe5", "add r13, r12")
    c.asm.label(ready + "_input")
    c.asm.store(cursor, 12)
    c.asm.store(end, 13)
    c.asm.mov_imm(0, 0)
    c.asm.store(key_mode)
    c.asm.mov_imm(0, routine.raw_address)
    c.asm.store(address)
    c.load(0, Address(cursor))
    c.asm.emit(b"\x48\x2d" + NATIVE_STACK_BUDGET.to_bytes(4, "little"), "sub rax, native_stack_budget")
    c.asm.store(floor)
    parsed = (
        c.call_c(Immediate(routine.raw_address), Address(cursor)) if model is None
        else model.parse(c, cursor, routine, fallback)
    )
    c.asm.load(12, cursor)
    # Reuse only bounded whitespace emission; the root's data is the input,
    # whereas the private routine's data is the address of this stack state.
    JsonCursor(c).whitespace()
    c.asm.emit(b"\x4d\x39\xec", "cmp r12, r13")
    c.asm.jump(fallback, "nz")
    # Constructors, default factories and field converters run only after the
    # complete document is valid. Their errors must not retry the operation.
    c.call_error_label = "error"
    c.transfer(parsed if model is None else model.construct(c), result)
    c.asm.jump(done)
    c.call_error_label = "error"
    c.asm.label(failure)
    c.call_c("PyErr_ExceptionMatches", c.constant(ValueError), result="pointer")
    c.asm.test_jump(0, fallback + "_clear", "nz", bits=32)
    c.call_c("PyErr_ExceptionMatches", c.constant(RecursionError), result="pointer")
    c.asm.test_jump(0, "error", bits=32)
    c.asm.label(fallback + "_clear")
    c.call_c("PyErr_Clear", result="void")
    c.asm.label(fallback)
    c.release(parsed)
    decoded = c.call(decode_fallback, c.data)
    c.transfer(decoded, result)
    c.asm.label(done)
    return c.finish(result).make_callable()
