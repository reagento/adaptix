import struct

from adaptix._internal.code_tools.native_numbers import float_layout_supported, integer_layout_supported
from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
from adaptix._internal.serialization.number_format import MAX_FIXED_FLOAT, MIN_FIXED_FLOAT
from adaptix._internal.serialization.x86_64.common import NATIVE_STACK_BUDGET, JsonEmitter, c_address

BUFFER = 0
BASE = 8
USED = 16
CAPACITY = 24
VALUE = 32
ROUTINE = 40
STACK_FLOOR = 48
INITIAL_CAPACITY = 256
DIGIT_PAIRS = b"".join(f"{value:02d}".encode() for value in range(100))


class JsonWriter(JsonEmitter):
    def __init__(self, compiler: X86Compiler, routines=None, *, float_formatter=None):
        super().__init__(compiler)
        self.routines = routines
        self.float_formatter = float_formatter
        if routines is not None:
            compiler.constants.extend(routines.values())
        self.done = compiler.label("write_done")
        self.invalid = compiler.label("unsupported_value")
        self.container_error = compiler.label("write_container_error")
        self.container_invalid = compiler.label("unsupported_container")
        self.container_done = compiler.label("write_container_done")

    def ensure(self, length):
        c = self.compiler
        enough, exact, resize = (c.label(name) for name in ("buffer_ready", "exact_capacity", "resize_buffer"))
        self.compiler.load(0, length)
        self.asm.emit(b"\x4c\x01\xe8", "add rax, r13")
        self.asm.jump(self.container_invalid if c.call_error_label == self.container_error else self.invalid, "o")
        required = c.slot()
        self.asm.store(required)
        self.asm.emit(b"\x4c\x39\xf0", "cmp rax, r14")
        self.asm.jump(enough, "be")
        self.asm.emit(b"\x4c\x89\xf0\x48\x01\xc0", "mov rax, r14; add rax, rax")
        self.asm.jump(exact, "o")
        self.asm.load(2, required)
        self.asm.emit(b"\x48\x39\xd0", "cmp rax, rdx")
        self.asm.jump(resize, "ae")
        self.asm.label(exact)
        self.asm.load(0, required)
        self.asm.label(resize)
        capacity, buffer = c.slot(), c.slot()
        self.asm.store(capacity)
        self.state_load(BUFFER)
        self.asm.store(buffer)
        # The unpublished bytes object has one owner, in the root's state.
        # Resize updates that owner too, including clearing it on failure.
        c.call_c("_PyBytes_Resize", c.data, capacity, result="int")
        self.state_load(BUFFER)
        self.asm.store(buffer)
        c.call_c("PyBytes_AsString", buffer, result="pointer")
        self.asm.emit(b"\x49\x89\xc4", "mov r12, rax")
        self.asm.load(14, capacity)
        self.state_store(BASE, 12)
        self.state_store(CAPACITY, 14)
        self.asm.label(enough)

    def append(self, pointer, length):
        c = self.compiler
        self.ensure(length)
        destination = c.slot()
        self.asm.emit(b"\x4b\x8d\x04\x2c", "lea rax, [r12+r13]")
        self.asm.store(destination)
        c.call_c(c_address("memcpy"), destination, pointer, length, result="void")
        c.load(0, length)
        self.asm.emit(b"\x49\x01\xc5", "add r13, rax")

    def byte(self, value: int):
        self.ensure(Immediate(1))
        self.asm.emit(b"\x43\xc6\x04\x2c" + bytes([value]), f"mov byte [r12+r13], {value}")
        self.asm.emit(b"\x49\xff\xc5", "inc r13")

    def emit(self):
        c = self.compiler
        c.reserve_loop_registers()
        self.stack_guard(STACK_FLOOR, self.invalid)
        for offset, register in ((BASE, 12), (USED, 13), (CAPACITY, 14), (VALUE, 15)):
            self.state_load(offset, register)
        value = c.slot()
        self.asm.store(value, 15)
        labels = {tp: c.label(tp.__name__) for tp in (str, int, float, bool, list, tuple, dict)}
        null = c.label("null")
        c.branch_if(value, None, null)
        if c.has_validated_object_header:
            for tp, label in labels.items():
                c.branch_if_type(value, tp, label)
        self.asm.jump(self.invalid)
        self.asm.label(null)
        self.append(self.literal(b"null"), Immediate(4))
        self.asm.jump(self.done)
        self.asm.label(labels[bool])
        false = c.label("false")
        c.branch_if(value, False, false)  # noqa: FBT003
        self.append(self.literal(b"true"), Immediate(4))
        self.asm.jump(self.done)
        self.asm.label(false)
        self.append(self.literal(b"false"), Immediate(5))
        self.asm.jump(self.done)
        for tp in (str, int, float, list, tuple, dict):
            self.asm.label(labels[tp])
            self.write_child(value, self.routines[tp])
            self.asm.jump(self.done)
        self.asm.label(self.invalid)
        self.fail(c.call_error_label)
        self.asm.label(self.done)
        self.state_store(USED, 13)
        c.call_error_label = "error"
        return c.finish(c.new_reference(None))

    def string(self, value):
        c = self.compiler
        length = c.slot()
        pointer = c.call_c("PyUnicode_AsUTF8AndSize", value, Address(length), result="pointer")
        self.asm.test_jump(0, c.call_error_label)
        scan, plain, escaped, finished = (
            c.label(name) for name in ("string_scan", "plain_string", "escaped_string", "string_written")
        )
        self.asm.load(2, pointer)
        self.asm.load(1, length)
        self.asm.emit(b"\x48\x01\xd1", "add rcx, rdx")
        self.string_vectors()
        self.asm.label(scan)
        self.string_chunk(scan, c.label("string_tail"), reader=False)
        self.asm.emit(b"\x48\x39\xca", "cmp rdx, rcx")
        self.asm.jump(plain, "ae")
        self.asm.emit(b"\x0f\xb6\x02", "movzx eax, byte [rdx]")
        for byte in (34, 92):
            self.asm.emit(b"\x83\xf8" + bytes([byte]), f"cmp eax, {byte}")
            self.asm.jump(escaped, "z")
        self.asm.emit(b"\x83\xf8\x20", "cmp eax, 32")
        self.asm.jump(escaped, "b")
        self.asm.emit(b"\x48\xff\xc2", "inc rdx")
        self.asm.jump(scan)
        self.asm.label(plain)
        self.byte(34)
        self.append(pointer, length)
        self.byte(34)
        self.asm.jump(finished)
        self.asm.label(escaped)
        self.escaped_string(pointer, length)
        self.asm.label(finished)

    def escaped_string(self, pointer, length):
        c = self.compiler
        # Reserve once so the copy loop neither allocates nor loses its cursors.
        # A control byte expands to at most six bytes: \\u00XX.
        c.load(0, length)
        self.asm.emit(b"\x48\x6b\xc0\x06", "imul rax, rax, 6")
        self.asm.jump(self.invalid, "o")
        self.asm.emit(b"\x48\x83\xc0\x02", "add rax, 2")
        self.asm.jump(self.invalid, "o")
        capacity = c.slot()
        self.asm.store(capacity)
        self.ensure(capacity)
        self.asm.load(2, pointer)
        self.asm.load(1, length)
        self.asm.emit(b"\x48\x01\xd1\x4f\x8d\x04\x2c", "add rcx, rdx; lea r8, [r12+r13]")
        self.asm.emit(b"\x41\xc6\x00\x22\x49\xff\xc0", "mov byte [r8], 34; inc r8")
        loop, escape, close = (c.label(name) for name in ("escape_loop", "escape_byte", "escape_end"))
        self.string_vectors()
        self.asm.label(loop)
        self.string_chunk(loop, c.label("escape_tail"), reader=False, copy=True)
        self.asm.emit(b"\x48\x39\xca", "cmp rdx, rcx")
        self.asm.jump(close, "ae")
        self.asm.emit(b"\x0f\xb6\x02", "movzx eax, byte [rdx]")
        for byte in (34, 92):
            self.asm.emit(b"\x83\xf8" + bytes([byte]), f"cmp eax, {byte}")
            self.asm.jump(escape, "z")
        self.asm.emit(b"\x83\xf8\x20", "cmp eax, 32")
        self.asm.jump(escape, "b")
        self.asm.emit(b"\x41\x88\x00\x49\xff\xc0\x48\xff\xc2", "mov [r8], al; inc r8; inc rdx")
        self.asm.jump(loop)
        self.asm.label(escape)
        short, next_byte = c.label("short_escape"), c.label("escape_next")
        for byte, encoded in ((34, 34), (92, 92), (8, 98), (9, 116), (10, 110), (12, 102), (13, 114)):
            missed = c.label("next_escape")
            self.asm.emit(b"\x83\xf8" + bytes([byte]), f"cmp eax, {byte}")
            self.asm.jump(missed, "nz")
            self.asm.mov_imm(0, encoded)
            self.asm.jump(short)
            self.asm.label(missed)
        self.asm.emit(b"\x41\xc7\x00\x5c\x75\x30\x30", "mov dword [r8], '\\u00'")
        c.load(11, self.literal(b"0123456789abcdef"))
        self.asm.emit(
            b"\x89\xc6\xc1\xee\x04\x41\x0f\xb6\x34\x33", "mov esi, eax; shr esi, 4; movzx esi, [r11+rsi]",
        )
        self.asm.emit(
            b"\x41\x88\x70\x04\x83\xe0\x0f\x41\x0f\xb6\x04\x03", "mov [r8+4], sil; and eax, 15; movzx eax, [r11+rax]",
        )
        self.asm.emit(b"\x41\x88\x40\x05\x49\x83\xc0\x06", "mov [r8+5], al; add r8, 6")
        self.asm.jump(next_byte)
        self.asm.label(short)
        self.asm.emit(
            b"\x41\xc6\x00\x5c\x41\x88\x40\x01\x49\x83\xc0\x02", "mov byte [r8], 92; mov [r8+1], al; add r8, 2",
        )
        self.asm.label(next_byte)
        self.asm.emit(b"\x48\xff\xc2", "inc rdx")
        self.asm.jump(loop)
        self.asm.label(close)
        self.asm.emit(b"\x41\xc6\x00\x22\x49\xff\xc0", "mov byte [r8], 34; inc r8")
        self.asm.emit(b"\x4d\x29\xe0\x4d\x89\xc5", "sub r8, r12; mov r13, r8")

    def integer(self, value):
        c = self.compiler
        number = self.integer_value(value)
        valid = c.label("integer_valid")
        self.asm.emit(b"\x48\x83\xf8\xff", "cmp rax, -1")
        self.asm.jump(valid, "nz")
        c.call_c("PyErr_Occurred", result="pointer")
        self.asm.test_jump(0, self.invalid, "nz")
        self.asm.label(valid)
        self.integer_number(number)

    def integer_number(self, number):
        c = self.compiler
        done = c.label("integer_written")
        self.small_integer(number, done)
        positive, digits, unsigned = (c.label(name) for name in ("positive", "digits", "unsigned"))
        buffer = [c.slot() for _ in range(4)][-1]
        c.load(8, Address(buffer))
        self.asm.emit(b"\x49\x83\xc0\x20\x4d\x89\xc1", "add r8, 32; mov r9, r8")
        self.asm.load(0, number)
        sign = c.slot()
        self.asm.store(sign)
        self.asm.test_jump(0, positive, "ns")
        self.asm.emit(b"\x48\xf7\xd8", "neg rax")
        self.asm.label(positive)
        self.asm.mov_imm(10, 0xCCCCCCCCCCCCCCCD)
        self.asm.label(digits)
        self.asm.emit(b"\x48\x89\xc1\x49\xf7\xe2\x48\xc1\xea\x03", "mov rcx, rax; mul r10; shr rdx, 3")
        self.asm.emit(
            b"\x48\x89\xd0\x48\x8d\x34\x92\x48\x01\xf6", "mov rax, rdx; lea rsi, [rdx+rdx*4]; add rsi, rsi",
        )
        self.asm.emit(b"\x48\x29\xf1\x89\xca", "sub rcx, rsi; mov edx, ecx")
        self.asm.emit(b"\x49\xff\xc9\x80\xc2\x30\x41\x88\x11", "dec r9; add dl, 48; mov [r9], dl")
        self.asm.test_jump(0, digits, "nz")
        self.asm.load(0, sign)
        self.asm.test_jump(0, unsigned, "ns")
        self.asm.emit(b"\x49\xff\xc9\x41\xc6\x01\x2d", "dec r9; mov byte [r9], 45")
        self.asm.label(unsigned)
        pointer, length = c.slot(), c.slot()
        self.asm.store(pointer, 9)
        self.asm.emit(b"\x4d\x29\xc8", "sub r8, r9")
        self.asm.store(length, 8)
        self.append(pointer, length)
        self.asm.label(done)

    def small_integer(self, number, done):
        c, a = self.compiler, self.asm
        positive, general = c.label("small_positive"), c.label("large_integer")
        a.load(0, number)
        a.test_jump(0, positive, "ns")
        a.emit(b"\x48\xf7\xd8", "neg rax")
        a.label(positive)
        a.emit(b"\x48\x3d\x10\x27\x00\x00", "cmp rax, 10000")
        a.jump(general, "ae")
        magnitude = c.slot()
        a.store(magnitude)
        self.ensure(Immediate(5))
        unsigned = c.label("small_unsigned")
        a.load(0, number)
        a.test_jump(0, unsigned, "ns")
        a.emit(b"\x43\xc6\x04\x2c\x2d\x49\xff\xc5", "mov byte [r12+r13], 45; inc r13")
        a.label(unsigned)
        a.emit(b"\x4f\x8d\x04\x2c", "lea r8, [r12+r13]")
        a.load(0, magnitude)
        one, two, three, low_pair = (
            c.label(name) for name in ("one_digit", "two_digits", "three_digits", "low_pair")
        )
        a.emit(b"\x83\xf8\x0a", "cmp eax, 10")
        a.jump(one, "b")
        c.load(9, self.literal(DIGIT_PAIRS))
        a.emit(b"\x83\xf8\x64", "cmp eax, 100")
        a.jump(two, "b")
        a.emit(b"\x89\xc2", "mov edx, eax")
        a.mov_imm(10, 0x51EB851F)
        a.emit(b"\x49\x0f\xaf\xc2\x48\xc1\xe8\x25", "imul rax, r10; shr rax, 37  # divide by 100")
        a.emit(b"\x6b\xf0\x64\x29\xf2", "imul esi, eax, 100; sub edx, esi")
        a.emit(b"\x83\xf8\x0a", "cmp eax, 10")
        a.jump(three, "b")
        a.emit(b"\x41\x0f\xb7\x0c\x41\x66\x41\x89\x08", "movzx ecx, word [r9+rax*2]; mov [r8], cx")
        a.emit(b"\x49\x83\xc0\x02\x49\x83\xc5\x02", "add r8, 2; add r13, 2")
        a.jump(low_pair)
        a.label(three)
        a.emit(
            b"\x04\x30\x41\x88\x00\x49\xff\xc0\x49\xff\xc5", "add al, 48; mov [r8], al; inc r8; inc r13",
        )
        a.label(low_pair)
        a.emit(b"\x89\xd0", "mov eax, edx")
        a.label(two)
        a.emit(
            b"\x41\x0f\xb7\x0c\x41\x66\x41\x89\x08\x49\x83\xc5\x02", "write last digit pair; add r13, 2",
        )
        a.jump(done)
        a.label(one)
        a.emit(b"\x04\x30\x41\x88\x00\x49\xff\xc5", "add al, 48; mov [r8], al; inc r13")
        a.jump(done)
        a.label(general)

    def integer_value(self, value):
        c = self.compiler
        if not c.has_validated_object_header or not integer_layout_supported():
            return c.call_c("PyLong_AsLongLong", value, result="pointer")
        wide, zero, positive, ready = (
            c.label(name) for name in ("wide_integer", "zero_integer", "positive_integer", "integer_value")
        )
        result = c.slot()
        self.asm.load(0, value)
        self.asm.emit(b"\x48\x8b\x48\x10\x48\x83\xf9\x10", "mov rcx, [rax+16]; cmp rcx, 16")
        self.asm.jump(wide, "ae")
        self.asm.emit(b"\xf6\xc1\x01", "test cl, 1")
        self.asm.jump(zero, "nz")
        self.asm.emit(b"\x8b\x40\x18\xf6\xc1\x02", "mov eax, [rax+24]; test cl, 2")
        self.asm.jump(positive, "z")
        self.asm.emit(b"\x48\xf7\xd8", "neg rax")
        self.asm.label(positive)
        self.asm.jump(ready)
        self.asm.label(zero)
        self.asm.emit(b"\x31\xc0", "xor eax, eax")
        self.asm.jump(ready)
        self.asm.label(wide)
        c.call_c("PyLong_AsLongLong", value, result="pointer")
        self.asm.label(ready)
        self.asm.store(result)
        return result

    def floating(self, value):
        c = self.compiler
        self.ensure(Immediate(32))
        kind = c.slot()
        if c.has_validated_object_header and float_layout_supported():
            self.asm.load(0, value)
            self.asm.emit(b"\xf2\x0f\x10\x40\x10", "movsd xmm0, [rax+16]")
        else:
            c.call_c("PyFloat_AsDouble", value, result="pointer")
        done = c.label("float_written")
        self.short_float(done)
        if self.float_formatter is not None:
            self.charconv_float()
            self.asm.label(done)
            return
        # Floating arguments occupy xmm0 independently of the integer ABI
        # registers. CPython's shortest-roundtrip formatter preserves repr.
        pointer = c.call_c(
            "PyOS_double_to_string", Immediate(114), Immediate(0), Immediate(2), Address(kind), result="pointer",
        )
        ready, invalid = c.label("float_buffer"), c.label("nonfinite_float")
        self.asm.test_jump(0, ready, "nz")
        c.call_c("PyErr_NoMemory")
        self.asm.jump(c.call_error_label)
        self.asm.label(ready)
        self.asm.load(0, kind)
        self.asm.test_jump(0, invalid, "nz", bits=32)
        length = c.call_c(c_address("strlen"), pointer, result="pointer")
        self.asm.emit(b"\x48\x83\xf8\x20", "cmp rax, 32")
        self.asm.jump(invalid, "a")
        destination = c.slot()
        self.asm.emit(b"\x4b\x8d\x04\x2c", "lea rax, [r12+r13]")
        self.asm.store(destination)
        c.call_c(c_address("memcpy"), destination, pointer, length, result="void")
        self.asm.load(0, length)
        self.asm.emit(b"\x49\x01\xc5", "add r13, rax")
        c.call_c("PyMem_Free", pointer, result="void")
        self.asm.jump(done)
        self.asm.label(invalid)
        c.call_c("PyMem_Free", pointer, result="void")
        self.asm.jump(self.invalid)
        self.asm.label(done)

    def charconv_float(self):
        c, a = self.compiler, self.asm
        c.constants.append(self.float_formatter.owner)
        fixed, scientific, selected, no_suffix = (
            c.label(name) for name in ("fixed_float", "scientific_float", "float_format", "float_no_suffix")
        )
        a.emit(b"\x66\x48\x0f\x7e\xc0", "movq rax, xmm0")
        a.mov_imm(1, (1 << 63) - 1)
        a.emit(b"\x48\x21\xc8", "and rax, rcx")
        a.mov_imm(1, 0x7FF0000000000000)
        a.emit(b"\x48\x39\xc8", "cmp rax, rcx  # infinity and NaN")
        a.jump(self.invalid, "ae")
        a.test_jump(0, fixed)
        a.mov_imm(1, struct.unpack("Q", struct.pack("d", MIN_FIXED_FLOAT))[0])
        a.emit(b"\x48\x39\xc8", "cmp rax, rcx")
        a.jump(scientific, "b")
        a.mov_imm(1, struct.unpack("Q", struct.pack("d", MAX_FIXED_FLOAT))[0])
        a.emit(b"\x48\x39\xc8", "cmp rax, rcx")
        a.jump(scientific, "ae")
        a.label(fixed)
        a.emit(b"\xf2\x48\x0f\x2c\xc0\xf2\x48\x0f\x2a\xd0", "cvttsd2si rax, xmm0; cvtsi2sd xmm2, rax")
        a.emit(b"\x66\x0f\x2e\xc2\x0f\x94\xc0\x0f\xb6\xc0", "ucomisd xmm0, xmm2; sete al; movzx eax, al")
        suffix, mode = c.slot(), c.slot()
        a.store(suffix)
        a.mov_imm(0, 2)
        a.store(mode)
        a.jump(selected)
        a.label(scientific)
        a.mov_imm(0, 0)
        a.store(suffix)
        a.mov_imm(0, 1)
        a.store(mode)
        a.label(selected)
        pointer, end = c.slot(), c.slot()
        a.emit(b"\x4b\x8d\x04\x2c", "lea rax, [r12+r13]")
        a.store(pointer)
        a.emit(b"\x48\x83\xc0\x1e", "add rax, 30")
        a.store(end)
        result = c.call_c(Immediate(self.float_formatter.address), pointer, end, mode, result="pointer")
        a.test_jump(2, self.invalid, "nz", bits=32)
        a.load(0, result)
        a.load(2, pointer)
        a.emit(b"\x48\x29\xd0\x49\x01\xc5", "sub rax, rdx; add r13, rax")
        a.load(0, suffix)
        a.test_jump(0, no_suffix)
        a.emit(b"\x66\x43\xc7\x04\x2c\x2e\x30\x49\x83\xc5\x02", "mov word [r12+r13], '.0'; add r13, 2")
        a.label(no_suffix)

    def short_float(self, done):
        c, a = self.compiler, self.asm
        general, unsigned = c.label("precise_float"), c.label("unsigned_float")
        environment = c.slot()
        displacement, mode = a.stack_displacement(environment)
        a.emit(b"\x0f\xae" + bytes([mode | 0x18]) + displacement, "stmxcsr [float_environment]")
        a.mark_write(environment)
        a.load(0, environment)
        a.emit(b"\xa9\x40\xe0\x00\x00", "test eax, 0xe040  # rounding, flush-to-zero, denormals-are-zero")
        a.jump(general, "nz")
        bits, number, whole, suffix = (c.slot() for _ in range(4))
        a.emit(b"\x66\x48\x0f\x7e\xc0", "movq rax, xmm0")
        a.store(bits)
        a.emit(b"\x48\x89\xc2", "mov rdx, rax")
        a.mov_imm(1, (1 << 63) - 1)
        a.emit(b"\x48\x21\xca", "and rdx, rcx  # float magnitude bits")
        a.mov_imm(1, struct.unpack("Q", struct.pack("d", 1e6))[0])
        a.emit(b"\x48\x39\xca", "cmp rdx, rcx")
        a.jump(general, "ae")
        a.emit(b"\x66\x48\x0f\x6e\xca\x66\x0f\x28\xd9", "movq xmm1, rdx; movapd xmm3, xmm1")
        c.load(11, self.literal(struct.pack("d", 10.0)))
        a.emit(b"\xf2\x41\x0f\x59\x0b", "mulsd xmm1, [r11]")
        a.emit(b"\xf2\x48\x0f\x2d\xc1", "cvtsd2si rax, xmm1")
        a.store(number)
        a.emit(b"\xf2\x48\x0f\x2a\xd0\xf2\x41\x0f\x5e\x13", "cvtsi2sd xmm2, rax; divsd xmm2, [r11]")
        a.emit(b"\x66\x0f\x2e\xd3", "ucomisd xmm2, xmm3")
        a.jump(general, "nz")
        # A tenth below 1e6 has a unique shortest decimal representation.
        # Require its exact float round trip; nearby values use CPython's dtoa.
        a.mov_imm(10, 0xCCCCCCCCCCCCCCCD)
        a.emit(b"\x49\xf7\xe2\x48\xc1\xea\x03\x48\x89\xd0", "mul r10; shr rdx, 3; mov rax, rdx")
        a.store(whole)
        a.load(1, number)
        a.emit(b"\x48\x8d\x34\x92\x48\x01\xf6\x48\x29\xf1", "lea rsi, [rdx+rdx*4]; add rsi, rsi; sub rcx, rsi")
        a.emit(b"\x83\xc1\x30\xc1\xe1\x08\x83\xc9\x2e", "add ecx, 48; shl ecx, 8; or ecx, 46")
        a.store(suffix, 1)
        a.load(0, bits)
        a.test_jump(0, unsigned, "ns")
        self.byte(45)
        a.label(unsigned)
        self.integer_number(whole)
        a.load(0, suffix)
        a.emit(b"\x66\x43\x89\x04\x2c\x49\x83\xc5\x02", "mov word [r12+r13], ax; add r13, 2")
        a.jump(done)
        a.label(general)

    def write_child(self, value, routine=None):
        c = self.compiler
        self.state_store(USED, 13)
        self.asm.load(0, value)
        self.state_store(VALUE)
        if routine is None:
            self.state_load(ROUTINE)
            address = c.slot()
            self.asm.store(address)
        else:
            address = Immediate(routine.raw_address)
        result = c.call_c(address, c.data)
        c.release(result)
        for offset, register in ((BASE, 12), (USED, 13), (CAPACITY, 14)):
            self.state_load(offset, register)

    def container(self, tp, value):  # noqa: PLR0915
        c = self.compiler
        c.call_c("Py_EnterRecursiveCall", self.literal(b" while encoding JSON"), result="pointer")
        self.asm.test_jump(0, "error", "nz", bits=32)
        c.call_error_label = self.container_error
        self.byte(123 if tp is dict else 91)
        index, first = c.slot(), c.slot()
        self.asm.mov_imm(0, 0)
        self.asm.store(index)
        self.asm.store(first)
        loop, close, item = (c.label(name) for name in ("write_items", "write_end", "write_item"))
        if tp is not dict:
            size = c.call_c("PyList_Size" if tp is list else "PyTuple_Size", value, result="pointer")
        else:
            key, child = c.slot(), c.slot()
        self.asm.label(loop)
        if tp is dict:
            c.call_c("PyDict_Next", value, Address(index), Address(key), Address(child), result="pointer")
            self.asm.test_jump(0, close, bits=32)
        else:
            self.asm.load(0, index)
            self.asm.load(2, size)
            self.asm.emit(b"\x48\x39\xd0", "cmp rax, rdx")
            self.asm.jump(close, "ae")
            c.call_c("PyList_GetItem" if tp is list else "PyTuple_GetItem", value, index, result="pointer")
            self.asm.test_jump(0, self.container_error)
            child = c.copy_loaded_reference()
        self.asm.load(0, first)
        self.asm.test_jump(0, item)
        self.byte(44)
        self.asm.label(item)
        self.asm.mov_imm(0, 1)
        self.asm.store(first)
        if tp is dict:
            self.asm.load(0, key)
            retained_key = c.copy_loaded_reference()
            self.asm.load(0, child)
            retained_child = c.copy_loaded_reference()
            if c.has_validated_object_header:
                c.branch_if_type(key, str, self.container_invalid, invert=True)
            else:
                self.asm.jump(self.container_invalid)
            self.string(key)
            self.byte(58)
        self.write_child(retained_child if tp is dict else child)
        if tp is dict:
            c.release(retained_key)
            c.release(retained_child)
        else:
            c.release(child)
        if tp is not dict:
            self.asm.load(0, index)
            self.asm.emit(b"\x48\xff\xc0", "inc rax")
            self.asm.store(index)
        self.asm.jump(loop)
        self.asm.label(close)
        self.byte(125 if tp is dict else 93)
        self.asm.jump(self.container_done)
        c.call_error_label = "error"


class ContainerWriter(JsonWriter):
    def emit_container(self, tp):
        c = self.compiler
        c.reserve_loop_registers()
        self.stack_guard(STACK_FLOOR, self.invalid)
        for offset, register in ((BASE, 12), (USED, 13), (CAPACITY, 14)):
            self.state_load(offset, register)
        value = c.slot()
        self.state_load(VALUE)
        self.asm.store(value)
        self.container(tp, value)
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
        self.state_store(USED, 13)
        return c.finish(c.new_reference(None))


def make_encoder(compiler_factory, encode_fallback, *, as_bytes, routine):  # noqa: PLR0915
    c = compiler_factory("json_encode_bytes" if as_bytes else "json_encode_str")
    c.constants.append(routine)
    # Only BUFFER owns a Python reference; the other words are raw state.
    slots = [c.slot() for _ in range(6)]
    buffer, base, used, capacity, value, address, floor = [*slots, c.slot(owned=True)][::-1]
    result = c.slot(owned=True)
    failure, fallback, done = (c.label(name) for name in ("encode_failure", "fallback", "encode_done"))
    c.call_error_label = failure
    output = c.call_c("PyBytes_FromStringAndSize", Immediate(0), Immediate(INITIAL_CAPACITY))
    c.transfer(output, buffer)
    pointer = c.call_c("PyBytes_AsString", buffer, result="pointer")
    c.asm.load(0, pointer)
    c.asm.store(base)
    c.asm.mov_imm(0, 0)
    c.asm.store(used)
    c.asm.mov_imm(0, INITIAL_CAPACITY)
    c.asm.store(capacity)
    c.asm.load(0, c.data)
    c.asm.store(value)
    c.asm.mov_imm(0, routine.raw_address)
    c.asm.store(address)
    c.load(0, Address(buffer))
    c.asm.emit(b"\x48\x2d" + NATIVE_STACK_BUDGET.to_bytes(4, "little"), "sub rax, native_stack_budget")
    c.asm.store(floor)
    written = c.call_c(Immediate(routine.raw_address), Address(buffer))
    c.release(written)
    if as_bytes:
        copy, ready = c.label("copy_small_output"), c.label("bytes_ready")
        c.asm.load(0, capacity)
        c.asm.emit(b"\x48\x3d" + INITIAL_CAPACITY.to_bytes(4, "little"), "cmp rax, initial_capacity")
        c.asm.jump(copy, "be")
        c.call_c("_PyBytes_Resize", Address(buffer), used, result="int")
        c.transfer(buffer, result)
        c.asm.jump(ready)
        c.asm.label(copy)
        c.transfer(c.call_c("PyBytes_FromStringAndSize", base, used), result)
        c.asm.label(ready)
    else:
        encoded = c.call_c(
            "PyUnicode_DecodeUTF8",
            base,
            used,
            Immediate(0),
        )
        c.transfer(encoded, result)
    c.asm.jump(done)
    c.call_error_label = "error"
    c.asm.label(failure)
    c.call_c("PyErr_ExceptionMatches", c.constant(ValueError), result="pointer")
    c.asm.test_jump(0, fallback, "nz", bits=32)
    c.call_c("PyErr_ExceptionMatches", c.constant(RecursionError), result="pointer")
    c.asm.test_jump(0, "error", bits=32)
    c.asm.label(fallback)
    c.call_c("PyErr_Clear", result="void")
    encoded_fallback = c.call(encode_fallback, c.data)
    c.transfer(encoded_fallback, result)
    c.asm.label(done)
    return c.finish(result).make_callable()
