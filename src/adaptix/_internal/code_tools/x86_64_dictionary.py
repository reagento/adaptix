import struct
from functools import partial
from typing import Literal

from adaptix._internal.code_tools.x86_64_assembler import REGISTERS, Slot


def emit_ordered_dictionary_row(compiler, data, names, expected_types, results, done):
    """Use fixed entry offsets when input field order matches the schema.

    Check every key and scalar type. Reordered/deleted entries continue to
    the learned-index path; fresh equal ASCII keys compare in a cold block.
    """
    failed = compiler.label("unordered_row")
    count = len(names)
    compiler.asm.emit(
        b"\x48\x81\x7a" + bytes([compiler.layout.keys_nentries]) + struct.pack("<i", count - 1),
        f"cmp QWORD PTR [rdx+24], {count - 1}",
    )
    compiler.asm.jump(failed, "be")
    compiler.asm.emit(b"\x0f\xb6\x4a" + bytes([compiler.layout.keys_index_bytes]), "movzx ecx, BYTE PTR [rdx+9]")
    compiler.asm.emit(b"\xb8\x01\x00\x00\x00\x48\xd3\xe0", "mov eax, 1; shl rax, cl")
    compiler.asm.emit(
        b"\x48\x8d\x54\x02" + bytes([compiler.layout.keys_indices]), "lea rdx, [rdx+rax+32]  # ordered unicode entries",
    )
    for index, (name, expected) in enumerate(zip(names, expected_types, strict=True)):
        offset = index * compiler.layout.unicode_entry_size
        compare, matched = compiler.label("compare_ordered_key"), compiler.label("ordered_key_matched")
        compiler.load(11, compiler.constant(name))
        compiler.asm.emit(b"\x4c\x39\x9a" + struct.pack("<i", offset), f"cmp [rdx+{offset}], r11")
        compiler.asm.jump(compare, "nz")
        compiler.asm.label(matched)
        compiler.asm.emit(
            b"\x48\x8b\x82" + struct.pack("<i", offset + compiler.layout.unicode_entry_value),
            f"mov rax, [rdx+{offset + compiler.layout.unicode_entry_value}]",
        )
        if expected is not None:
            compiler.check_dictionary_scalar(expected, failed)
        compiler.asm.emit(b"\x48\x89\xc7", "mov rdi, rax")
        compiler.incref_rdi(nonnull=True)
        compiler.asm.store(results[index], 7)
        compiler.cold_handlers.append(
            partial(compiler.ordered_key_compare, name, offset, compare, matched, failed),
        )
    compiler.asm.jump(done)
    compiler.asm.label(failed)
    for value in results:
        compiler.release(value, retained=True)
    compiler.asm.load(7, data)
    compiler.asm.emit(
        b"\x48\x8b\x57" + bytes([compiler.layout.dict_keys]), "mov rdx, [rdi+32]  # restore keys for learned row",
    )


def emit_ordered_key_compare(compiler, name, offset, compare, matched, failed):
    compiler.asm.label(compare)
    compiler.asm.emit(b"\x48\x8b\x82" + struct.pack("<i", offset), f"mov rax, [rdx+{offset}]")
    compiler.asm.test_jump(0, failed)
    compiler.match_ascii_key(name, failed)
    compiler.asm.jump(matched)


def emit_match_ascii_key(compiler, name: str, failed: str, *, source: Literal[0, 1] = 0):
    """Compare a short compact ASCII string in rax or rcx without calls."""
    try:
        remaining = name.encode("ascii")
    except UnicodeEncodeError:
        compiler.asm.jump(failed)
        return
    if len(remaining) > 32:  # noqa: PLR2004
        compiler.asm.jump(failed)
        return
    compiler.asm.emit(
        b"\x48\x83" + bytes([0x78 | source, compiler.layout.unicode_length, len(remaining)]),
        f"cmp QWORD PTR [{REGISTERS[source]}+16], {len(remaining)}",
    )
    compiler.asm.jump(failed, "nz")
    flags = (
        b"\x8b\x48" + bytes([compiler.layout.unicode_state]) + b"\x83\xe1\x60\x83\xf9\x60" if source == 0 else
        b"\x8b\x41" + bytes([compiler.layout.unicode_state]) + b"\x83\xe0\x60\x83\xf8\x60"
    )
    compiler.asm.emit(flags, "check compact ASCII flags")
    compiler.asm.jump(failed, "nz")
    offset = compiler.layout.unicode_ascii_data
    scratch = 1 if source == 0 else 9
    for width in (8, 4, 2, 1):
        while len(remaining) >= width:
            value = int.from_bytes(remaining[:width], "little")
            if width == 8:  # noqa: PLR2004
                compiler.asm.mov_imm(scratch, value)
                compiler.asm.emit(
                    bytes([0x48 | ((scratch >> 3) << 2), 0x39, 0x48 | source, offset]),
                    f"cmp QWORD PTR [{REGISTERS[source]}+{offset}], {REGISTERS[scratch]}",
                )
            else:
                prefix = b"\x66" if width == 2 else b""  # noqa: PLR2004
                opcode = b"\x80" if width == 1 else b"\x81"
                compiler.asm.emit(
                    prefix + opcode + bytes([0x78 | source, offset]) + value.to_bytes(width, "little"),
                    f"cmp key bytes at [{REGISTERS[source]}+{offset}], 0x{value:x}",
                )
            compiler.asm.jump(failed, "nz")
            remaining = remaining[width:]
            offset += width


def emit_probe_dictionary(compiler, mapping: Slot, key: str, missing: str, generic: str) -> None:
    """Return a borrowed value in rdi without calls or dictionary snapshots.

    Combined Unicode tables with at most 128 buckets use signed byte
    indices. Follow CPython's perturb sequence, including deleted buckets;
    every other layout uses the ordinary C API. All reads stay under the GIL.
    """
    layout = compiler.layout
    if (
        layout is None or layout.dict_values is None or layout.dict_keys is None
        or layout.keys_kind is None or layout.keys_index_bytes is None or layout.keys_indices is None
        or layout.unicode_entry_size is None or layout.unicode_entry_value is None
    ):
        raise RuntimeError("Dictionary probing requires a complete CPython dictionary layout")
    compiler.branch_if_type(mapping, dict, generic, invert=True)
    compiler.asm.load(7, mapping)
    compiler.asm.emit_memory(b"\x48\x83", 0x3F, layout.dict_values, "check combined dictionary", immediate=b"\x00")
    compiler.asm.jump(generic, "nz")
    compiler.asm.emit_memory(b"\x48\x8b", 0x57, layout.dict_keys, "mov rdx, dictionary keys")
    compiler.asm.emit_memory(b"\x80", 0x3A, layout.keys_kind, "check Unicode entries", immediate=b"\x01")
    compiler.asm.jump(generic, "nz")
    compiler.asm.emit_memory(b"\x0f\xb6", 0x4A, layout.keys_index_bytes, "movzx ecx, index byte exponent")
    compiler.asm.emit(b"\x83\xf9\x07", "cmp ecx, 7  # signed byte indices")
    compiler.asm.jump(generic, "a")
    compiler.asm.emit(b"\x41\xba\x01\x00\x00\x00\x49\xd3\xe2", "mov r10d, 1; shl r10, cl")
    compiler.asm.emit_memory(b"\x48\x8d", 0x72, layout.keys_indices, "lea rsi, dictionary indices")
    compiler.asm.emit(
        b"\x4c\x01\xd2\x48\x83\xc2" + bytes([layout.keys_indices]),
        "add rdx, index byte count and header",
    )
    compiler.asm.emit(b"\x49\xff\xca", "dec r10  # bucket mask")
    compiler.asm.mov_imm(9, hash(key) & ((1 << 64) - 1))
    compiler.asm.emit(b"\x4d\x89\xc8\x4d\x21\xd0", "mov r8, r9; and r8, r10  # first bucket")
    compiler.load(11, compiler.constant(key))
    probe, advance, matched = (compiler.label(prefix) for prefix in ("probe_key", "probe_next", "probe_matched"))
    compiler.asm.label(probe)
    compiler.asm.emit(b"\x42\x0f\xbe\x04\x06", "movsx eax, BYTE PTR [rsi+r8]")
    compiler.asm.emit(b"\x83\xf8\xff", "cmp eax, -1  # empty bucket proves absence")
    compiler.asm.jump(missing, "z")
    compiler.asm.emit(b"\x83\xf8\xfe", "cmp eax, -2  # deleted bucket")
    compiler.asm.jump(advance, "z")
    compiler.asm.emit(
        b"\x48\xc1\xe0" + bytes([layout.unicode_entry_size.bit_length() - 1]), "scale Unicode entry index",
    )
    compiler.asm.emit(
        b"\x48\x8d\x3c\x02\x48\x8b\x07\x4c\x39\xd8", "lea rdi, [rdx+rax]; mov rax, [rdi]; cmp rax, r11",
    )
    compiler.asm.jump(matched, "z")
    compiler.match_ascii_key(key, advance)
    compiler.asm.label(matched)
    compiler.asm.emit_memory(b"\x48\x8b", 0x7F, layout.unicode_entry_value, "mov rdi, borrowed field value")
    ready = compiler.label("probe_ready")
    compiler.asm.jump(ready)
    compiler.asm.label(advance)
    compiler.asm.emit(b"\x49\xc1\xe9\x05", "shr r9, 5  # perturb shift")
    compiler.asm.emit(b"\x4f\x8d\x44\x80\x01\x4d\x01\xc8\x4d\x21\xd0", "lea r8, [r8+r8*4+1]; add r8, r9; and r8, r10")
    compiler.asm.jump(probe)
    compiler.asm.label(ready)
