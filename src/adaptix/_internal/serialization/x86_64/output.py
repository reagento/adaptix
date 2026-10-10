import json

from adaptix._internal.code_tools.x86_64_assembler import Immediate
from adaptix._internal.serialization.plan import ListOutput, ModelOutput, ScalarOutput
from adaptix._internal.serialization.x86_64.writer import (
    BASE,
    CAPACITY,
    STACK_FLOOR,
    USED,
    VALUE,
    ContainerWriter,
    JsonWriter,
)


class OutputWriter(JsonWriter):
    def __init__(self, compiler, output, children, float_formatter):
        super().__init__(compiler, float_formatter=float_formatter)
        self.output = output
        self.children = children

    def emit(self):
        c = self.compiler
        c.reserve_loop_registers()
        self.stack_guard(STACK_FLOOR, self.invalid)
        for offset, register in ((BASE, 12), (USED, 13), (CAPACITY, 14)):
            self.state_load(offset, register)
        value = c.slot()
        self.state_load(VALUE)
        self.asm.store(value)
        if not c.has_validated_object_header:
            self.asm.jump(self.invalid)
        elif isinstance(self.output, ScalarOutput):
            self.scalar(self.output, value)
        elif isinstance(self.output, ListOutput):
            self.sequence(value)
        else:
            self.model(value)
        self.asm.jump(self.done)
        self.asm.label(self.invalid)
        self.fail("error")
        self.asm.label(self.done)
        self.state_store(USED, 13)
        return c.finish(c.new_reference(None))

    def scalar(self, output, value):
        c = self.compiler
        done = c.label("scalar_written")
        labels = [(tp, c.label("scalar_" + tp.__name__)) for tp in output.types]
        for tp, label in labels:
            c.branch_if_type(value, tp, label)
        self.asm.jump(self.invalid)
        for tp, label in labels:
            self.asm.label(label)
            if tp is str:
                self.string(value)
            elif tp is int:
                self.integer(value)
            elif tp is float:
                self.floating(value)
            elif tp is bool:
                false, ready = c.label("false"), c.label("bool_written")
                c.branch_if(value, False, false)  # noqa: FBT003
                self.append(self.literal(b"true"), Immediate(4))
                self.asm.jump(ready)
                self.asm.label(false)
                self.append(self.literal(b"false"), Immediate(5))
                self.asm.label(ready)
            else:
                self.append(self.literal(b"null"), Immediate(4))
            self.asm.jump(done)
        self.asm.label(done)

    def child(self, output, value):
        c = self.compiler
        routine = self.children[output]
        c.constants.append(routine)
        self.state_store(USED, 13)
        self.asm.load(0, value)
        self.state_store(VALUE)
        result = c.call_c(Immediate(routine.raw_address), c.data)
        c.release(result)
        for offset, register in ((BASE, 12), (USED, 13), (CAPACITY, 14)):
            self.state_load(offset, register)

    def model(self, value):
        fields = self.output.fields
        c = self.compiler
        values = c.get_attrs(value, tuple(name for _, name, _ in fields), fallback_label=self.invalid)
        for index, ((key, _, output), raw) in enumerate(zip(fields, values, strict=True)):
            prefix = (b"{" if index == 0 else b",") + json.encoder.encode_basestring(key).encode("utf-8") + b":"
            self.append(self.literal(prefix), Immediate(len(prefix)))
            self.child(output, raw)
            c.release(raw)
        self.byte(125)

    def sequence(self, value):
        c = self.compiler
        c.branch_if_type(value, list, self.invalid, invert=True)
        self.byte(91)
        index = c.slot()
        self.asm.mov_imm(0, 0)
        self.asm.store(index)
        size = c.call_c("PyList_Size", value, result="pointer")
        loop, close, item = (c.label(name) for name in ("list_items", "list_end", "list_item"))
        self.asm.label(loop)
        self.asm.load(0, index)
        self.asm.load(2, size)
        self.asm.emit(b"\x48\x39\xd0", "cmp rax, rdx")
        self.asm.jump(close, "ae")
        self.asm.test_jump(0, item)
        self.byte(44)
        self.asm.label(item)
        c.call_c("PyList_GetItem", value, index, result="pointer")
        self.asm.test_jump(0, "error")
        scalar_item = isinstance(self.output.item, ScalarOutput)
        raw = c.slot() if scalar_item else c.copy_loaded_reference()
        if scalar_item:
            self.asm.store(raw)
        if scalar_item:
            self.scalar(self.output.item, raw)
        else:
            self.child(self.output.item, raw)
        if not scalar_item:
            c.release(raw)
        self.asm.load(0, index)
        self.asm.emit(b"\x48\xff\xc0", "inc rax")
        self.asm.store(index)
        self.asm.jump(loop)
        self.asm.label(close)
        self.byte(93)


def make_output_writer(compiler_factory, output, float_formatter, routines=None):
    routines = {} if routines is None else routines
    if output in routines:
        return routines[output]
    children = (
        [child for _, _, child in output.fields] if isinstance(output, ModelOutput) else
        [output.item] if isinstance(output, ListOutput) and not isinstance(output.item, ScalarOutput) else []
    )
    routines.update({
        child: make_output_writer(compiler_factory, child, float_formatter, routines)
        for child in children
    })
    routine = OutputWriter(compiler_factory("json_write_typed"), output, routines, float_formatter).emit()
    routines[output] = routine
    return routine


def make_generic_writer(compiler_factory, float_formatter):
    routines = {
        tp: make_output_writer(compiler_factory, ScalarOutput((tp,)), float_formatter)
        for tp in (str, int, float)
    }
    routines.update({
        tp: ContainerWriter(compiler_factory("json_write_" + tp.__name__)).emit_container(tp)
        for tp in (list, tuple, dict)
    })
    return JsonWriter(compiler_factory("json_write_value"), routines).emit()
