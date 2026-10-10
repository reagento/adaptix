from adaptix._internal.code_tools.x86_64_assembler import Address, Immediate
from adaptix._internal.model_tools.definitions import DefaultFactory, DefaultValue
from adaptix._internal.morphing.model import native_runtime
from adaptix._internal.morphing.native.registry import get_program
from adaptix._internal.serialization.x86_64.reader import KEY_INDEX, JsonCursor


class ModelReader:
    def __init__(self, plan):
        self.plan = plan
        self.fields = {}
        self.key_order = ()

    def parse(self, compiler, cursor, routine, fallback):  # noqa: PLR0915
        c, asm = compiler, compiler.asm
        if not c.has_validated_object_header:
            asm.jump(fallback)
            return c.slot(owned=True)
        stream = JsonCursor(c)
        self.fields = {field.id: c.slot(owned=True) for field in self.plan.shape.fields}
        labels = {key: c.label("field_" + child.id) for key, child in self.plan.name_layout.crown.map.items()}
        loop, close, after = (c.label(name) for name in ("model_fields", "model_end", "model_next"))
        stream.whitespace()
        stream.peek(fallback)
        stream.compare(123, fallback, "nz")
        stream.advance()
        stream.whitespace()
        stream.peek(fallback)
        stream.compare(125, close)
        asm.label(loop)
        stream.peek(fallback)
        stream.compare(34, fallback, "nz")
        key = self.read(c, cursor, routine, key=True)
        key_index = c.slot()
        c.load(11, Address(cursor))
        asm.emit(b"\x49\x8b\x43" + bytes([KEY_INDEX]), "mov rax, [r11+40]  # schema key index")
        asm.store(key_index)
        stream.whitespace()
        stream.peek(fallback)
        stream.compare(58, fallback, "nz")
        stream.advance()
        raw = self.read(c, cursor, routine, key=False)
        escaped = c.label("escaped_field_name")
        asm.load(0, key_index)
        asm.test_jump(0, escaped, "s")
        if self.key_order:
            self.dispatch(c, tuple(labels[name] for name in self.key_order))
        asm.label(escaped)
        # Escaped names and noncanonical strings still compare by value.
        for name, label in labels.items():
            c.call_c("PyUnicode_Compare", key, c.constant(name), result="pointer")
            asm.test_jump(0, label, bits=32)
        asm.jump(after)
        for name, label in labels.items():
            asm.label(label)
            field = self.fields[self.plan.name_layout.crown.map[name].id]
            c.release(field)
            c.transfer(raw, field)
            asm.jump(after)
        asm.label(after)
        c.release(key)
        c.release(raw)
        stream.whitespace()
        stream.peek(fallback)
        stream.compare(125, close)
        stream.compare(44, fallback, "nz")
        stream.advance()
        stream.whitespace()
        asm.jump(loop)
        asm.label(close)
        stream.advance()
        asm.store(cursor, 12)
        for field in self.plan.shape.fields:
            value = self.fields[field.id]
            accepted = c.label("field_valid")
            if field.is_optional:
                c.branch_if_null(value, accepted)
            else:
                c.branch_if_null(value, fallback)
            program = get_program(self.plan.field_loaders[field.id])
            for tp in program.types:
                c.branch_if_type(value, tp, accepted)
            if program.coerce_int:
                c.branch_if_type(value, int, accepted)
            if program.nullable:
                c.branch_if(value, None, accepted)
            asm.jump(fallback)
            asm.label(accepted)
        return c.slot(owned=True)

    def dispatch(self, c, labels, start=0):
        if len(labels) == 1:
            c.asm.jump(labels[0])
            return
        middle = len(labels) // 2
        left = c.label("field_index_left")
        c.asm.emit(b"\x3d" + (start + middle).to_bytes(4, "little"), f"cmp eax, {start + middle}")
        c.asm.jump(left, "b")
        self.dispatch(c, labels[middle:], start + middle)
        c.asm.label(left)
        self.dispatch(c, labels[:middle], start)

    def read(self, c, cursor, routine, *, key):
        c.asm.store(cursor, 12)
        c.asm.mov_imm(0, int(key))
        # State slots are contiguous in memory, from cursor upward.
        c.load(11, Address(cursor))
        c.asm.emit(b"\x49\x89\x43\x10", "mov [r11+16], rax  # key mode")
        if key:
            c.asm.mov_imm(0, (1 << 64) - 1)
            c.asm.emit(b"\x49\x89\x43" + bytes([KEY_INDEX]), "mov [r11+40], rax  # unknown key index")
        value = c.call_c(Immediate(routine.raw_address), Address(cursor))
        c.asm.load(12, cursor)
        return value

    def construct(self, c):
        if not c.has_validated_object_header:
            return c.slot(owned=True)
        for field in self.plan.shape.fields:
            value = self.fields[field.id]
            if field.is_optional:
                present, ready = c.label("explicit_field"), c.label("field_ready")
                c.branch_if_null(value, present, invert=True)
                if not self.plan.props.use_default_for_omitted:
                    default = c.new_reference(native_runtime.MISSING)
                elif isinstance(field.default, DefaultFactory):
                    default = c.call(field.default.factory)
                elif isinstance(field.default, DefaultValue):
                    default = c.new_reference(field.default.value)
                else:
                    raise TypeError("Unsupported model default")
                c.transfer(default, value)
                c.asm.jump(ready)
                c.asm.label(present)
            converted = c.inline_call(self.plan.field_loaders[field.id], value)
            c.release(value)
            c.transfer(converted, value)
            if field.is_optional:
                c.asm.label(ready)
        args = tuple(self.fields[param.field_id] for param in self.plan.shape.params)
        result = c.construct_object(
            self.plan.shape.constructor, args, (), tuple(param.name for param in self.plan.shape.params),
            steal=True, omitted=None if self.plan.props.use_default_for_omitted else native_runtime.MISSING,
        )
        for value in self.fields.values():
            c.release(value)
        return result
