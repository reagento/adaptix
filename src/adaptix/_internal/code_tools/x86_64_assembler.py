import struct
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass
from typing import Literal, cast


@dataclass(frozen=True)
class Slot:
    index: int

    @property
    def offset(self) -> int:
        return -8 * (self.index + 1)


@dataclass(frozen=True)
class Immediate:
    value: int


@dataclass(frozen=True)
class Address:
    slot: Slot


FlowEvent = tuple[Literal["label", "jump", "branch"], str] | tuple[Literal["write", "clear"], Slot]


class X86Assembler:
    """Encode the instructions needed by the native object compiler.

    Registers use their hardware encoding (rax=0, rcx=1, ..., r15=15).
    Stack operands use the shortest displacement from rbp.
    """

    def __init__(self):
        self.code = bytearray()
        self.lines: list[str] = []
        self.labels: dict[str, int] = {}
        self.final_labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []
        self.flow: list[FlowEvent] = []

    def emit(self, code: bytes, text: str) -> None:
        self.code.extend(code)
        self.lines.append(f"    {text}")

    def emit_memory(
        self, opcode: bytes, operand: int, offset: int, text: str, *, immediate: bytes = b"",
    ) -> None:
        if operand & 7 == 4:  # noqa: PLR2004
            raise ValueError("Indexed memory operands require a SIB encoding")
        if offset == 0 and operand & 7 != 5:  # noqa: PLR2004
            displacement, mode = b"", 0
        elif -(1 << 7) <= offset < (1 << 7):
            displacement, mode = struct.pack("<b", offset), 0x40
        else:
            displacement, mode = struct.pack("<i", offset), 0x80
        self.emit(opcode + bytes([(operand & 0x3F) | mode]) + displacement + immediate, text)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"Duplicate assembly label {name}")
        self.labels[name] = len(self.code)
        self.lines.append(f"{name}:")
        self.flow.append(("label", name))

    def mov_imm(self, register: int, value: int) -> None:
        if 0 <= value < (1 << 32):
            prefix = b"\x41" if register >= 8 else b""  # noqa: PLR2004
            name = REGISTERS32[register]
            self.emit(prefix + bytes([0xB8 + (register & 7)]) + struct.pack("<I", value), f"mov {name}, 0x{value:x}")
            return
        self.emit(
            bytes([0x48 | (register >> 3), 0xB8 + (register & 7)]) + struct.pack("<Q", value),
            f"mov {REGISTERS[register]}, 0x{value:x}",
        )

    def load(self, register: int, slot: Slot) -> None:
        displacement, mode = self.stack_displacement(slot)
        self.emit(
            bytes([0x48 | ((register >> 3) << 2), 0x8B, mode | ((register & 7) << 3)]) + displacement,
            f"mov {REGISTERS[register]}, [rbp{slot.offset:+}]",
        )

    def store(self, slot: Slot, register: int = 0, *, clear: bool = False) -> None:
        displacement, mode = self.stack_displacement(slot)
        self.emit(
            bytes([0x48 | ((register >> 3) << 2), 0x89, mode | ((register & 7) << 3)]) + displacement,
            f"mov [rbp{slot.offset:+}], {REGISTERS[register]}",
        )
        self.flow.append(("clear" if clear else "write", slot))

    def mark_clear(self, slot: Slot) -> None:
        """Record a proven NULL value at a control-flow merge, without emitting code."""
        self.flow.append(("clear", slot))

    def mark_write(self, slot: Slot) -> None:
        self.flow.append(("write", slot))

    def clear(self, *slots: Slot) -> None:
        self.emit(b"\x31\xc0", "xor eax, eax")
        for slot in slots:
            self.store(slot, clear=True)

    def test_jump(self, register: int, label: str, condition: str = "z", *, bits: Literal[32, 64] = 64) -> None:
        prefix = bytes([(0x48 if bits == 64 else 0x40) | ((register >> 3) * 5)])  # noqa: PLR2004
        operand = (register & 7) * 9
        names = REGISTERS if bits == 64 else REGISTERS32  # noqa: PLR2004
        self.emit(
            (prefix if prefix != b"\x40" else b"") + bytes([0x85, 0xC0 | operand]),
            f"test {names[register]}, {names[register]}",
        )
        self.jump(label, condition)

    def lea(self, register: int, slot: Slot) -> None:
        displacement, mode = self.stack_displacement(slot)
        self.emit(
            bytes([0x48 | ((register >> 3) << 2), 0x8D, mode | ((register & 7) << 3)]) + displacement,
            f"lea {REGISTERS[register]}, [rbp{slot.offset:+}]",
        )

    @staticmethod
    def stack_displacement(slot: Slot) -> tuple[bytes, int]:
        return (
            (struct.pack("<b", slot.offset), 0x45) if slot.offset >= -(1 << 7) else
            (struct.pack("<i", slot.offset), 0x85)
        )

    def jump(self, label: str, condition: str | None = None) -> None:
        opcode = {
            None: b"\xe9", "z": b"\x0f\x84", "nz": b"\x0f\x85", "s": b"\x0f\x88", "ae": b"\x0f\x83",
            "ns": b"\x0f\x89",
            "be": b"\x0f\x86", "a": b"\x0f\x87", "b": b"\x0f\x82",
        }[condition]
        self.emit(opcode + b"\x00" * 4, f"j{condition or 'mp'} {label}")
        self.fixups.append((len(self.code) - 4, label))
        self.flow.append(("branch" if condition is not None else "jump", label))

    def finish(self) -> bytes:
        branches = self.branch_fixups()
        short, relocate = self.relax_branches(branches)
        self.final_labels = {label: relocate(position) for label, position in self.labels.items()}
        code = bytearray()
        cursor = 0
        for start, end, label, opcode in branches:
            code.extend(self.code[cursor:start])
            target = self.final_labels[label]
            if start in short:
                code.extend(opcode + struct.pack("<b", target - len(code) - 2))
            else:
                code.extend(self.code[start:end - 4])
                code.extend(struct.pack("<i", target - len(code) - 4))
            cursor = end
        code.extend(self.code[cursor:])
        return bytes(code)

    def branch_fixups(self):
        branches = []
        for offset, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"Undefined assembly label {label}")
            unconditional = self.code[offset - 1] == 0xE9  # noqa: PLR2004
            start = offset - (1 if unconditional else 2)
            opcode = b"\xeb" if unconditional else bytes([self.code[offset - 1] - 0x10])
            branches.append((start, offset + 4, label, opcode))
        branches.sort()
        return branches

    def relax_branches(self, branches):
        """Shorten to a fixed point; shrinking code cannot widen another jump.

        Keep the original offsets for composing assemblers and inserting call
        context. Only final encoding and final_labels use the relaxed layout.
        """
        short: set[int] = set()
        while True:
            relocate = self.branch_layout(branches, short)
            additions = set()
            for start, end, label, _ in branches:
                if start in short:
                    continue
                target = self.labels[label]
                distance = relocate(target) - relocate(start) - 2
                if target >= end:
                    distance -= end - start - 2
                if -(1 << 7) <= distance < (1 << 7):
                    additions.add(start)
            if not additions:
                return short, relocate
            short.update(additions)

    @staticmethod
    def branch_layout(branches, short):
        ends, savings = [], [0]
        for start, end, _, _ in branches:
            if start in short:
                ends.append(end)
                savings.append(savings[-1] + end - start - 2)

        def relocate(position):
            return position - savings[bisect_right(ends, position)]

        return relocate

    def extend(self, other: "X86Assembler") -> None:
        if self.labels.keys() & other.labels.keys():
            raise ValueError("Duplicate assembly labels")
        offset = len(self.code)
        self.code.extend(other.code)
        self.lines.extend(other.lines)
        self.labels.update({name: position + offset for name, position in other.labels.items()})
        self.fixups.extend((position + offset, label) for position, label in other.fixups)
        self.flow.extend(other.flow)

    def definitely_null_at(self, label: str, initially_null: list[Slot]) -> frozenset[Slot]:
        """Intersect NULL facts over every path, including recovery blocks and loops.

        Unknown jump targets are terminal error exits. A slot can be omitted
        from successful cleanup only if all paths reaching that point clear it.
        """
        labels = {cast(str, operand): index for index, (kind, operand) in enumerate(self.flow) if kind == "label"}
        slots = dict.fromkeys(initially_null)
        slots.update(dict.fromkeys(cast(Slot, operand) for kind, operand in self.flow if kind in {"write", "clear"}))
        bits = {slot: 1 << index for index, slot in enumerate(slots)}
        incoming: list[int | None] = [None] * len(self.flow)
        incoming[0] = sum(bits[slot] for slot in set(initially_null))
        queued = bytearray(len(self.flow))
        queued[0] = 1
        pending = deque([0])
        while pending:
            index = pending.popleft()
            queued[index] = 0
            kind, operand = self.flow[index]
            state = cast(int, incoming[index])
            if kind == "write":
                state &= ~bits[cast(Slot, operand)]
            elif kind == "clear":
                state |= bits[cast(Slot, operand)]
            successors = []
            if kind in {"jump", "branch"} and operand in labels:
                successors.append(labels[cast(str, operand)])
            if kind != "jump" and index + 1 < len(self.flow):
                successors.append(index + 1)
            for successor in successors:
                previous = incoming[successor]
                merged = state if previous is None else previous & state
                if previous != merged:
                    incoming[successor] = merged
                    if not queued[successor]:
                        queued[successor] = 1
                        pending.append(successor)
        final = incoming[labels[label]] or 0
        return frozenset(slot for slot, bit in bits.items() if final & bit)


REGISTERS = (
    "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
)
REGISTERS32 = (
    "eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi",
    "r8d", "r9d", "r10d", "r11d", "r12d", "r13d", "r14d", "r15d",
)
ARG_REGISTERS = (7, 6, 2, 1, 8, 9)
