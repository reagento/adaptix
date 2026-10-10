import ctypes

from adaptix._internal.code_tools.x86_64_assembler import REGISTERS, Immediate
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler

NATIVE_STACK_BUDGET = 8192


class JsonFallback(ValueError):
    pass


class JsonEmitter:
    def __init__(self, compiler: X86Compiler):
        self.compiler = compiler
        self.asm = compiler.asm

    def state_load(self, offset: int, register: int = 0):
        self.asm.load(11, self.compiler.data)
        self.asm.emit(
            bytes([0x49 | ((register >> 3) << 2), 0x8B, 0x43 | ((register & 7) << 3), offset]),
            f"mov {REGISTERS[register]}, [r11+{offset}]  # state",
        )

    def state_store(self, offset: int, register: int = 0):
        self.asm.load(11, self.compiler.data)
        self.asm.emit(
            bytes([0x49 | ((register >> 3) << 2), 0x89, 0x43 | ((register & 7) << 3), offset]),
            f"mov [r11+{offset}], {REGISTERS[register]}  # state",
        )

    def string_vectors(self):
        for register, byte in ((2, 34), (3, 92), (4, 31)):
            self.compiler.load(11, self.literal(bytes([byte]) * 16))
            self.asm.emit(bytes([0xF3, 0x41, 0x0F, 0x6F, register * 8 + 3]), f"movdqu xmm{register}, [r11]")
        self.asm.emit(b"\x66\x0f\xef\xf6", "pxor xmm6, xmm6")

    def string_chunk(self, loop: str, scalar: str, *, reader: bool, copy: bool = False):
        if reader:
            self.asm.emit(b"\x4c\x89\xe8\x4c\x29\xe0", "mov rax, r13; sub rax, r12")
        else:
            self.asm.emit(b"\x48\x89\xc8\x48\x29\xd0", "mov rax, rcx; sub rax, rdx")
        self.asm.emit(b"\x48\x83\xf8\x10", "cmp rax, 16")
        self.asm.jump(scalar, "b")
        self.asm.emit(b"\xf3\x41\x0f\x6f\x04\x24" if reader else b"\xf3\x0f\x6f\x02", "movdqu xmm0, [cursor]")
        if copy:
            self.asm.emit(b"\xf3\x41\x0f\x7f\x00", "movdqu [r8], xmm0")
        self.asm.emit(b"\x66\x0f\x6f\xc8\x66\x0f\x74\xca", "movdqa xmm1, xmm0; pcmpeqb xmm1, xmm2")
        self.asm.emit(b"\x66\x0f\x6f\xe8\x66\x0f\x74\xeb", "movdqa xmm5, xmm0; pcmpeqb xmm5, xmm3")
        self.asm.emit(b"\x66\x0f\xeb\xcd", "por xmm1, xmm5")
        self.asm.emit(b"\x66\x0f\xd8\xc4\x66\x0f\x74\xc6", "psubusb xmm0, xmm4; pcmpeqb xmm0, xmm6")
        self.asm.emit(b"\x66\x0f\xeb\xc8\x66\x0f\xd7\xc1", "por xmm1, xmm0; pmovmskb eax, xmm1")
        special = self.compiler.label("special_byte")
        self.asm.test_jump(0, special, "nz", bits=32)
        self.asm.emit(b"\x49\x83\xc4\x10" if reader else b"\x48\x83\xc2\x10", "add cursor, 16")
        if copy:
            self.asm.emit(b"\x49\x83\xc0\x10", "add r8, 16")
        self.asm.jump(loop)
        self.asm.label(special)
        self.asm.emit(b"\x0f\xbc\xc0", "bsf eax, eax")
        self.asm.emit(b"\x49\x01\xc4" if reader else b"\x48\x01\xc2", "add cursor, rax")
        if copy:
            self.asm.emit(b"\x49\x01\xc0", "add r8, rax")
        self.asm.label(scalar)

    def stack_guard(self, offset: int, exhausted: str):
        # CPython's recursion count does not account for our larger frames.
        # Bound native nesting in bytes; the root retries with the reference codec.
        self.state_load(offset)
        self.asm.emit(b"\x48\x39\xc4", "cmp rsp, rax")
        self.asm.jump(exhausted, "b")

    def literal(self, value: bytes):
        buffer = ctypes.create_string_buffer(value)
        self.compiler.constants.append(buffer)
        return Immediate(ctypes.addressof(buffer))

    def fail(self, label: str):
        self.compiler.call_c("PyErr_SetNone", self.compiler.constant(JsonFallback), result="void")
        self.asm.jump(label)


def c_address(name: str):
    return Immediate(ctypes.cast(getattr(ctypes.CDLL(None), name), ctypes.c_void_p).value)
