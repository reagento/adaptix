from dataclasses import dataclass

from adaptix._internal.code_tools.x86_64_assembler import Immediate
from adaptix._internal.morphing.native.plan import IterablePlan
from adaptix._internal.morphing.native.registry import identity_spec
from adaptix._internal.morphing.native.x86_64.iterable import (
    check_scalar_list_item,
    check_sequence_mapping,
    check_sequence_type,
    list_layout_supported,
    map_iterator,
    map_list,
    tuple_item_offset,
)
from adaptix._internal.morphing.native.x86_64.scalar import get_program


@dataclass(frozen=True)
class SetProgram(IterablePlan):
    spec: tuple

    def emit(self, c):
        generic, done = c.label("set_slow"), c.label("set_done")
        result = c.slot(owned=True)
        if self.loading:
            check_sequence_type(c, list, generic)
            if self.strict_coercion:
                check_sequence_mapping(c, list)
            converted = copy_scalar_set(c, self.spec, self.fallback, self.origin)
        else:
            c.branch_if_type(c.data, self.origin, generic, invert=True)
            converted = c.call_c("PySequence_List" if self.dump_as is list else "PySequence_Tuple", c.data)
        c.transfer(converted, result)
        if not self.loading and (self.spec[0] or self.spec[1]):
            validate_set_snapshot(c, result, self.spec, self.dump_as, generic)
        c.asm.jump(done)
        return c.fallback_result(result, self.fallback, generic, done, cleanup=(result,))


def copy_scalar_set(c, spec, fallback, origin):
    generic, done, loop, finished = (
        c.label(prefix) for prefix in ("scalar_set_slow", "scalar_set_done", "scalar_set_loop", "scalar_set_end")
    )
    result = c.call_c("PySet_New", Immediate(0))
    index, item = c.slot(), c.slot()
    c.asm.emit(b"\x31\xc0", "zero set input index")
    c.asm.store(index)
    c.asm.label(loop)
    c.asm.load(1, index)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x3b\x48" + bytes([c.layout.var_size]), "compare set input index and current list size")
    c.asm.jump(finished, "ae")
    c.asm.emit(b"\x48\x8b\x40" + bytes([c.layout.list_items]) + b"\x48\x8b\x3c\xc8", "load scalar set input item")
    c.asm.store(item, 7)
    for register, cls in zip((9, 10), spec[0], strict=False):
        c.load(register, c.constant(cls))
    if spec[1]:
        c.load(11, c.constant(None))
    check_scalar_list_item(c, *spec, generic)
    c.call_c("PySet_Add", result, item, result="int")
    c.asm.load(0, index)
    c.asm.emit(b"\x48\xff\xc0", "advance set input index")
    c.asm.store(index)
    c.asm.jump(loop)
    c.asm.label(finished)
    if origin is frozenset:
        converted = c.call_c("PyFrozenSet_New", result)
        c.release(result)
        c.transfer(converted, result)
    c.asm.jump(done)
    return c.fallback_result(result, fallback, generic, done, cleanup=(result,))


@dataclass(frozen=True)
class MappedSetProgram(IterablePlan):
    def emit(self, c):
        options = vars(self)
        if self.loading:
            return map_list(c, **options, output_type=self.origin)
        generic, done = c.label("mapped_set_slow"), c.label("mapped_set_done")
        result = c.slot(owned=True)
        c.branch_if_type(c.data, self.origin, generic, invert=True)
        value = map_iterator(c, **options, output_type=self.dump_as)
        c.transfer(value, result)
        c.asm.jump(done)
        return c.fallback_result(result, self.fallback, generic, done)


def validate_set_snapshot(c, result, spec, output_type, generic):
    loop, done = c.label("set_validate_loop"), c.label("set_validate_done")
    c.asm.load(0, result)
    c.asm.emit(b"\x4c\x8b\x40" + bytes([c.layout.var_size]), "load snapshot length")
    if output_type is list:
        c.asm.emit(b"\x48\x8b\x50" + bytes([c.layout.list_items]), "load snapshot items")
    else:
        c.asm.emit(b"\x48\x8d\x50" + bytes([tuple_item_offset()]), "load tuple snapshot items")
    c.asm.emit(b"\x31\xc9", "zero snapshot index")
    types, nullable = spec
    for register, cls in zip((9, 10), types, strict=False):
        c.load(register, c.constant(cls))
    if nullable:
        c.load(11, c.constant(None))
    c.asm.label(loop)
    c.asm.emit(b"\x4c\x39\xc1", "compare index and length")
    c.asm.jump(done, "ae")
    c.asm.emit(b"\x48\x8b\x3c\xca", "load set snapshot member")
    check_scalar_list_item(c, types, nullable, generic)
    c.asm.emit(b"\x48\xff\xc1", "advance snapshot index")
    c.asm.jump(loop)
    c.asm.label(done)


def build_set_program(plan: IterablePlan, c):
    spec = identity_spec(plan.mapper)
    if spec is None and get_program(plan.mapper) is None:
        return None
    if not c.has_validated_object_header or not list_layout_supported():
        return None
    return (
        SetProgram(spec=spec, **vars(plan))
        if spec is not None and (spec[0] or spec[1] or not plan.loading)
        else MappedSetProgram(**vars(plan))
    )
