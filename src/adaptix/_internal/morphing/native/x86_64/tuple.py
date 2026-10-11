import ctypes
import sys
from dataclasses import dataclass
from functools import partial

from adaptix._internal.code_tools.x86_64_assembler import Immediate
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.native.plan import TuplePlan
from adaptix._internal.morphing.native.registry import identity_spec
from adaptix._internal.morphing.native.runtime import ErrorState, check_tuple_input, finish_tuple, handle_error
from adaptix._internal.morphing.native.x86_64.iterable import (
    check_list_mapping,
    copy_identity_sequence,
)
from adaptix._internal.morphing.native.x86_64.scalar import ScalarProgram, get_program


@dataclass(frozen=True)
class TupleProgram(TuplePlan):
    specs: tuple
    offset: int

    def emit(self, c):
        generic, done, tuple_input, snapshotted, invalid = (
            c.label(prefix) for prefix in ("tuple_slow", "tuple_done", "tuple_input", "tuple_snapshot", "tuple_invalid")
        )
        result = c.slot(owned=True)
        c.branch_if_type(c.data, tuple, tuple_input)
        if not self.loading:
            c.asm.jump(generic)
        else:
            c.branch_if_type(c.data, list, generic, invert=True)
            self.mapping_guard(c, list)
            copied = c.call_c("PyList_AsTuple", c.data)
            c.transfer(copied, result)
            c.asm.jump(snapshotted)
        c.asm.label(tuple_input)
        self.mapping_guard(c, tuple)
        c.asm.load(0, c.data)
        c.asm.emit(
            b"\x48\x81\x78" + bytes([c.layout.var_size]) + len(self.specs).to_bytes(4, "little"),
            "check fixed tuple length",
        )
        c.asm.jump(generic, "nz")
        copied = copy_identity_sequence(c, tuple, tuple)
        c.transfer(copied, result)
        c.asm.label(snapshotted)
        c.asm.load(0, result)
        c.asm.emit(
            b"\x48\x81\x78" + bytes([c.layout.var_size]) + len(self.specs).to_bytes(4, "little"),
            "check snapshot length",
        )
        c.asm.jump(invalid, "nz")
        validate_tuple_scalars(c, result, self.specs, self.offset, invalid)
        c.asm.jump(done)
        c.asm.label(invalid)
        converted = c.call(self.snapshot_fallback, result)
        c.release(result)
        c.transfer(converted, result)
        c.asm.jump(done)
        return c.fallback_result(result, self.fallback, generic, done)

    def mapping_guard(self, c, input_type):
        if self.loading and self.strict_coercion:
            from adaptix._internal.morphing import constant_length_tuple_provider  # noqa: PLC0415

            check_list_mapping(
                c, input_type=input_type, check=check_tuple_input,
                module=constant_length_tuple_provider, attribute="CollectionsMapping",
            )


def validate_tuple_scalars(c, source, specs, offset, invalid):
    for index, spec in enumerate(specs):
        if not spec[0] and not spec[1]:
            continue
        accepted = c.label("tuple_item_valid")
        c.asm.load(0, source)
        c.asm.emit(b"\x48\x8b\x80" + (offset + index * 8).to_bytes(4, "little"), "load tuple scalar")
        if spec[1]:
            c.load(11, c.constant(None))
            c.asm.emit(b"\x4c\x39\xd8", "cmp rax, r11")
            c.asm.jump(accepted, "z")
        for cls in spec[0]:
            c.load(11, c.constant(cls))
            c.asm.emit(b"\x4c\x39\x58" + bytes([c.layout.object_type]), "cmp tuple scalar type")
            c.asm.jump(accepted, "z")
        c.asm.jump(invalid)
        c.asm.label(accepted)




@dataclass(frozen=True)
class MappedTupleProgram(TuplePlan):
    offset: int
    identity_specs: tuple | None = None

    def emit(self, c):
        generic, done, tuple_input, validated, invalid = (
            c.label(prefix) for prefix in (
                "tuple_mapper_slow", "tuple_mapper_done", "tuple_mapper_input",
                "tuple_mapper_valid", "tuple_mapper_size",
            )
        )
        result = c.slot(owned=True)
        c.branch_if_type(c.data, tuple, tuple_input)
        if self.loading:
            c.branch_if_type(c.data, list, generic, invert=True)
            TupleProgram.mapping_guard(self, c, list)
            c.asm.jump(validated)
        else:
            c.asm.jump(generic)
        c.asm.label(tuple_input)
        TupleProgram.mapping_guard(self, c, tuple)
        c.asm.label(validated)
        snapshot = c.call_c("PySequence_Tuple", c.data)
        c.asm.load(0, snapshot)
        c.asm.emit(
            b"\x48\x81\x78" + bytes([c.layout.var_size]) + len(self.mappers).to_bytes(4, "little"),
            "check fixed tuple length",
        )
        c.asm.jump(invalid, "nz")
        if self.identity_specs is not None:
            self.emit_identity_result(c, snapshot, result, done)
        created = c.call_c("PyTuple_New", Immediate(len(self.mappers)))
        c.transfer(created, result)
        c.call_c("PyObject_GC_UnTrack", result, result="void")
        state = c.lazy_call(ErrorState) if self.debug_trail != DebugTrail.DISABLE else None
        for index, mapper in enumerate(self.mappers):
            displacement = (self.offset + index * 8).to_bytes(4, "little")
            c.asm.load(0, snapshot)
            c.asm.emit(b"\x48\x8b\x80" + displacement, "load fixed tuple member")
            item = c.copy_loaded_reference()
            value = (
                c.inline_call(
                    mapper, item, partial(handle_error, self.debug_trail, self.loading), state, c.constant(index),
                )
                if state is not None else c.inline_call(mapper, item)
            )
            c.release(item)
            c.asm.load(0, result)
            c.asm.load(11, value)
            c.asm.emit(b"\x4c\x89\x98" + displacement, "transfer fixed tuple member")
            c.asm.clear(value)
        c.release(snapshot)
        c.finish_lazy_state(state, partial(finish_tuple, self.loading), "tuple_mapper_no_errors")
        c.call_c("PyObject_GC_Track", result, result="void")
        c.asm.jump(done)
        c.asm.label(invalid)
        converted = c.call(self.snapshot_fallback, snapshot)
        c.release(snapshot)
        c.transfer(converted, result)
        c.asm.jump(done)
        return c.fallback_result(result, self.fallback, generic, done)

    def emit_identity_result(self, c, snapshot, result, done):
        mapped, tuple_input = c.label("tuple_needs_mapping"), c.label("tuple_identity_copy")
        validate_tuple_scalars(c, snapshot, self.identity_specs, self.offset, mapped)
        c.branch_if_type(c.data, tuple, tuple_input)
        # The snapshot of a list is already a new tuple. Exact scalar values
        # need no conversion, so it is also the complete result.
        c.transfer(snapshot, result)
        c.asm.jump(done)
        c.asm.label(tuple_input)
        copy_identity_sequence(c, tuple, tuple, destination=result)
        c.release(snapshot)
        c.asm.jump(done)
        c.asm.label(mapped)


def build_tuple_program(plan: TuplePlan, c):
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        return None
    specs = tuple(identity_spec(mapper) for mapper in plan.mappers)
    offset = c.layout.tuple_items
    probe = (object(), object())
    if not c.has_validated_object_header or ctypes.c_void_p.from_address(id(probe) + offset).value != id(probe[0]):
        return None
    identity_specs = None
    if any(spec is None for spec in specs) and any(spec is not None for spec in specs):
        candidates = []
        for mapper, spec in zip(plan.mappers, specs, strict=True):
            scalar = get_program(mapper)
            candidates.append(
                (tuple(cls for cls in scalar.types if cls is not int or not scalar.coerce_int), scalar.nullable)
                if isinstance(scalar, ScalarProgram)
                else spec,
            )
        if all(spec is not None for spec in candidates):
            identity_specs = tuple(candidates)
    options = {**vars(plan), "mappers": tuple(plan.mappers)}
    return (
        MappedTupleProgram(offset=offset, identity_specs=identity_specs, **options)
        if any(spec is None for spec in specs) else TupleProgram(specs=specs, offset=offset, **options)
    )
