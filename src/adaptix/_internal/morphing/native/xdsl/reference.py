from dataclasses import dataclass

from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
from adaptix._internal.definitions import CodeGenBackend
from adaptix._internal.morphing.model.crown_definitions import ExtraForbid
from adaptix._internal.morphing.native.bytecodes import CheckType, ReadField
from adaptix._internal.morphing.native.codegen import publish
from adaptix._internal.morphing.native.plan import ModelDumperPlan, ModelLoaderPlan
from adaptix._internal.morphing.native.xdsl.generator import UnsupportedPlan, model_fallback, model_loader_fields


@dataclass(eq=False)
class ReferenceCodeGenerator:
    """Match the LLVM model algorithm with the existing instruction encoder."""

    def compile(self, plan, *, hook):
        if not isinstance(plan, ModelLoaderPlan):
            return model_fallback(plan) if isinstance(plan, ModelDumperPlan) else plan.fallback
        fallback = model_fallback(plan)
        try:
            ir = model_loader_fields(plan)
        except UnsupportedPlan:
            return fallback
        crown = plan.name_layout.crown
        c = X86Compiler(plan.name)
        slow, done = c.label("reference_fallback"), c.label("reference_done")
        result = c.slot(owned=True)
        c.branch_if_type(c.data, dict, slow, invert=True)
        c.load(0, c.data)
        c.asm.emit_memory(b"\x48\x8b", 0x00, c.layout.dict_keys, "load dictionary keys")
        c.asm.emit_memory(b"\x80", 0x38, c.layout.keys_kind, "check unicode dictionary", immediate=b"\x01")
        c.asm.jump(slow, "nz")
        if isinstance(crown.extra_policy, ExtraForbid):
            c.call_c("PyDict_Size", c.data, result="pointer")
            c.asm.mov_imm(11, len(ir.required_keys))
            c.asm.emit(b"\x4c\x39\xd8", "check exact field count")
            c.asm.jump(slow, "nz")
        values = {}
        for op in ir.operations:
            if isinstance(op, ReadField):
                hash(op.key)
                value = c.call_c("PyDict_GetItemWithError", c.data, c.constant(op.key), result="pointer")
                present = c.label("reference_field_present")
                c.branch_if_null(value, present, invert=True)
                c.call_c("PyErr_Occurred", result="pointer")
                c.asm.test_jump(0, c.call_error_label, "nz")
                c.asm.jump(slow)
                c.asm.label(present)
                values[op.target] = value
            elif isinstance(op, CheckType):
                accepted = c.label("reference_type_ok")
                for cls in op.types:
                    c.branch_if_type(values[op.target], cls, accepted)
                c.asm.jump(slow)
                c.asm.label(accepted)
        args = tuple(c.copy_reference(values[param.field_id]) for param in plan.shape.params)
        solved = c.vectorcall_address(c.constant(plan.shape.constructor), args, ())
        for arg in reversed(args):
            c.release(arg, nonnull=True)
        c.transfer(solved, result)
        c.asm.jump(done)
        c.asm.label(slow)
        c.transfer(c.call(fallback, c.data), result)
        c.asm.label(done)
        return publish(c.finish(result), hook, CodeGenBackend.X86_64)
