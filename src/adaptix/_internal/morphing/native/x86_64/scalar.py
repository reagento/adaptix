from dataclasses import dataclass

from adaptix._internal.morphing.native import descriptions
from adaptix._internal.morphing.native.registry import get_program as get_description
from adaptix._internal.morphing.native.runtime import decimal_error, retry_scalar


def get_program(function):
    description = get_description(function)
    if description is None or hasattr(description, "emit"):
        return description
    from adaptix._internal.morphing.native.x86_64.base64 import Base64Program  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.datetime import DateTimeProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.enum import EnumProgram, can_inline_enum  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.optional import OptionalProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.union import LiteralProgram, UnionDumperProgram  # noqa: PLC0415
    from adaptix._internal.morphing.native.x86_64.uuid import UUIDProgram  # noqa: PLC0415

    if isinstance(description, descriptions.EnumProgram) and not can_inline_enum(description):
        return None
    emitters = {
        descriptions.ScalarProgram: ScalarProgram,
        descriptions.DecimalProgram: DecimalProgram,
        descriptions.Base64Program: Base64Program,
        descriptions.DateTimeProgram: DateTimeProgram,
        descriptions.EnumProgram: EnumProgram,
        descriptions.OptionalProgram: OptionalProgram,
        descriptions.LiteralProgram: LiteralProgram,
        descriptions.UnionDumperProgram: UnionDumperProgram,
        descriptions.UUIDProgram: UUIDProgram,
    }
    emitter = emitters[type(description)]
    return emitter(**vars(description))




@dataclass(frozen=True)
class DecimalProgram(descriptions.DecimalProgram):
    def emit(self, c):
        import ctypes  # noqa: PLC0415
        from decimal import Decimal  # noqa: PLC0415

        if self.loading and not hasattr(ctypes.pythonapi, "PyObject_CallOneArg"):
            return c.call(self.function, c.data)
        generic, done = c.label("decimal_slow"), c.label("decimal_done")
        result = c.slot(owned=True)
        if self.loading:
            text = c.label("decimal_text")
            c.branch_if_type(c.data, str, text)
            c.branch_if_type(c.data, Decimal, generic, invert=True)
            value = c.copy_reference(c.data)
            c.transfer(value, result)
            c.asm.jump(done)
            c.asm.label(text)
            value = c.guarded_c_call(
                "PyObject_CallOneArg", (c.constant(Decimal), c.data), decimal_error, c.data,
            )
        else:
            c.branch_if_type(c.data, Decimal, generic, invert=True)
            value = c.call_c("PyObject_Str", c.data)
        c.transfer(value, result)
        c.asm.jump(done)
        return c.fallback_result(result, self.function, generic, done)


@dataclass(frozen=True)
class ScalarProgram(descriptions.ScalarProgram):
    supports_consuming = True

    def emit(self, c, *, consume=False):
        accepted, generic, done = (c.label(prefix) for prefix in ("scalar_ok", "scalar_slow", "scalar_done"))
        result = c.data if consume else c.slot(owned=True)
        function = descriptions.resolve_function(self.function)
        integer = c.label("scalar_integer") if self.coerce_int else None
        c.asm.load(0, c.data)
        if self.nullable:
            c.load(11, c.constant(None))
            c.asm.emit(b"\x4c\x39\xd8", "check nullable scalar")
            c.asm.jump(accepted, "z")
        c.asm.emit(b"\x48\x8b\x50" + bytes([c.layout.object_type]), "load scalar type once")
        if self.coerce_int:
            c.load(11, c.constant(int))
            c.asm.emit(b"\x4c\x39\xda", "check integer coercion")
            c.asm.jump(integer, "z")
        for cls in self.types:
            c.load(11, c.constant(cls))
            c.asm.emit(b"\x4c\x39\xda", "check accepted scalar type")
            c.asm.jump(accepted, "z")
        c.asm.jump(generic)
        if self.coerce_int:
            c.asm.label(integer)
            value = convert_integer_float(c, function)
            if consume:
                c.release(c.data, nonnull=True)
            c.transfer(value, result)
            c.asm.jump(done)
        c.asm.label(accepted)
        if not consume:
            value = c.copy_reference(c.data)
            c.transfer(value, result)
        c.asm.jump(done)
        c.asm.label(generic)
        value = c.call(function, c.data)
        if consume:
            c.release(c.data, nonnull=True)
        c.transfer(value, result)
        c.asm.label(done)
        return result




def convert_integer_float(c, function):
    from adaptix._internal.morphing.native.x86_64.union import integer_layout_supported  # noqa: PLC0415

    if not integer_layout_supported():
        return c.guarded_c_call("PyNumber_Float", (c.data,), retry_scalar, c.constant(function), c.data)
    wide, zero, positive, ready, done = (
        c.label(prefix) for prefix in ("wide_integer_float", "zero_integer_float", "positive_integer_float",
                                      "compact_integer_float", "integer_float_done")
    )
    result = c.slot(owned=True)
    c.asm.load(0, c.data)
    c.asm.emit(b"\x48\x8b\x48" + bytes([c.layout.long_tag]) + b"\x48\x83\xf9\x10", "check compact integer digit count")
    c.asm.jump(wide, "ae")
    c.asm.emit(b"\xf6\xc1\x01", "check zero integer tag")
    c.asm.jump(zero, "nz")
    c.asm.emit(b"\x8b\x40" + bytes([c.layout.long_digits]) + b"\xf6\xc1\x02", "load integer digit; check sign")
    c.asm.jump(positive, "z")
    c.asm.emit(b"\x48\xf7\xd8", "negate integer digit")
    c.asm.label(positive)
    c.asm.jump(ready)
    c.asm.label(zero)
    c.asm.emit(b"\x31\xc0", "zero integer magnitude")
    c.asm.label(ready)
    c.asm.emit(b"\xf2\x48\x0f\x2a\xc0", "convert compact integer to double in xmm0")
    converted = c.guarded_c_call("PyFloat_FromDouble", (), retry_scalar, c.constant(function), c.data)
    c.transfer(converted, result)
    c.asm.jump(done)
    c.asm.label(wide)
    converted = c.guarded_c_call("PyNumber_Float", (c.data,), retry_scalar, c.constant(function), c.data)
    c.transfer(converted, result)
    c.asm.label(done)
    return result
