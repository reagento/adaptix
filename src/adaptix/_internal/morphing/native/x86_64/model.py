from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property, partial
from typing import Generic, TypeVar

from adaptix._internal.code_tools.x86_64_assembler import Immediate, Slot
from adaptix._internal.code_tools.x86_64_compiler import MAX_INLINE_CODE_SIZE, X86Compiler
from adaptix._internal.common import Loader
from adaptix._internal.definitions import CodeGenBackend, DebugTrail
from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    DescriptorAccessor,
    InputField,
    ItemAccessor,
    OutputField,
    ParamKind,
)
from adaptix._internal.morphing.model import native_runtime as runtime
from adaptix._internal.morphing.model.basic_gen import CodeGenHook
from adaptix._internal.morphing.model.crown_definitions import (
    CrownPath,
    ExtraCollect,
    ExtraExtract,
    ExtraKwargs,
    ExtraSaturate,
    ExtraSkip,
    ExtraTargets,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
)
from adaptix._internal.morphing.native.bytecodes import FieldBlock, Operation, ReadScalarFields, emit_field_block
from adaptix._internal.morphing.native.codegen import publish
from adaptix._internal.morphing.native.model_ir import build_model_fields
from adaptix._internal.morphing.native.optimizer import fuse_scalar_reads
from adaptix._internal.morphing.native.plan import ModelDumperPlan, ModelLoaderPlan
from adaptix._internal.morphing.native.registry import IDENTITY_LOADERS
from adaptix._internal.morphing.native.x86_64.fields import X86FieldBackend
from adaptix._internal.special_cases_optimization import as_is_stub, get_default_clause

MODEL_INLINE_CODE_SIZE = 32768


@dataclass(frozen=True)
class ModelProgram:
    plan: ModelLoaderPlan | ModelDumperPlan
    compiler_factory: Callable[[str], X86Compiler]
    flat_fallback: Loader | None = None
    loader_ir: FieldBlock | None = None

    @property
    def inline_budget(self) -> int | None:
        # Bound duplicated model code in a parent while keeping scalar reads
        # fused. Dumpers retain their existing inlining policy.
        return MODEL_INLINE_CODE_SIZE if isinstance(self.plan, ModelLoaderPlan) else None

    def emit(self, compiler: X86Compiler) -> Slot:
        if isinstance(self.plan, ModelLoaderPlan):
            loader_gen = NativeModelLoaderGen(
                self.plan,
                self.compiler_factory,
                flat_fallback=self.flat_fallback,
            )
            if self.loader_ir is not None:
                loader_gen.field_ir = self.loader_ir
            loader_gen.compiler = compiler
            return loader_gen.optional_result() if self.flat_fallback is not None else loader_gen.inline_result()
        dumper_gen = NativeModelDumperGen(self.plan, self.compiler_factory)
        dumper_gen.compiler = compiler
        return dumper_gen.compile_result()


ModelPlanT = TypeVar("ModelPlanT", ModelLoaderPlan, ModelDumperPlan)


@dataclass
class NativeModelGen(Generic[ModelPlanT]):
    plan: ModelPlanT
    compiler_factory: Callable[[str], X86Compiler]
    flat_fallback: Loader | None = None
    compiler: X86Compiler = field(init=False, repr=False)

    def discard(self, function, *args):
        self.compiler.release(self.compiler.call(function, *args))

    def finish(self, result: Slot, hook: CodeGenHook, *, inline=False):
        program = self.make_program() if inline else None
        return publish(self.compiler.finish(result, program=program), hook, CodeGenBackend.X86_64)

    def make_program(self) -> ModelProgram:
        return ModelProgram(self.plan, self.compiler_factory, self.flat_fallback)


class NativeModelLoaderGen(NativeModelGen[ModelLoaderPlan]):
    @cached_property
    def field_ir(self) -> FieldBlock:
        return fuse_scalar_reads(build_model_fields(self.plan), defer_last=self.flat_fallback is None)

    def make_program(self) -> ModelProgram:
        return ModelProgram(self.plan, self.compiler_factory, self.flat_fallback, self.field_ir)

    def compile(self, hook: CodeGenHook):  # noqa: C901
        self.compiler = self.compiler_factory(self.plan.name)
        if self.can_inline():
            return self.compile_inline(hook)
        c = self.compiler
        self.state = c.call(partial(runtime.LoadState, self.plan.debug_trail, self.plan.model_identity))
        self.values = c.call_c("PyObject_GetAttr", self.state, c.constant("values"))
        self.node(self.plan.name_layout.crown, (), c.data)
        extra_move = self.plan.name_layout.extra_move
        if isinstance(extra_move, ExtraTargets):
            use_extra = self.plan.name_layout.crown.extra_policy == ExtraCollect()
            for field_id in extra_move.fields:
                field = self.plan.shape.fields_dict[field_id]
                raw = c.call(partial(runtime.get_load_extra, field, use_extra=use_extra), self.state)
                self.convert(field, (), raw)
                c.release(raw)
        self.discard(runtime.finish_load, self.state)

        args_list = c.call_c("PyList_New", Immediate(0))
        kwargs = c.call_c("PyDict_New")
        skipped_param = False
        for param in self.plan.shape.params:
            field = self.plan.shape.fields_dict[param.field_id]
            if field.id in self.plan.skipped_fields:
                skipped_param = True
                continue
            if skipped_param and param.kind == ParamKind.POS_ONLY:
                raise ValueError("Cannot generate consistent constructor call, positional-only parameter is skipped")
            packed = (
                field.is_optional
                and not (
                    self.plan.props.use_default_for_omitted
                    and isinstance(field.default, (DefaultValue, DefaultFactory))
                )
                and not (isinstance(extra_move, ExtraTargets) and field.id in extra_move.fields)
            )
            value = c.dict_lookup(self.values, field.id, runtime.MISSING)
            skip = c.label("omitted_param")
            c.branch_if(value, runtime.MISSING, skip)
            if param.kind == ParamKind.KW_ONLY or skipped_param or packed:
                c.call_c("PyDict_SetItem", kwargs, c.constant(param.name), value, result="int")
            else:
                c.call_c("PyList_Append", args_list, value, result="int")
            c.asm.label(skip)
            c.release(value)
        if isinstance(extra_move, ExtraKwargs):
            extra = c.call_c("PyObject_GetAttr", self.state, c.constant("extra"))
            # Unlike dict.update, **kwargs rejects duplicate keyword arguments.
            self.discard(merge_constructor_extra, kwargs, extra)
        args = c.call_c("PyList_AsTuple", args_list)
        result = c.call_c("PyObject_Call", c.constant(self.plan.shape.constructor), args, kwargs)
        if isinstance(extra_move, ExtraSaturate):
            extra = c.call_c("PyObject_GetAttr", self.state, c.constant("extra"))
            self.discard(extra_move.func, result, extra)
        fallback = self.finish(result, hook)
        if self.can_inline_optional():
            self.flat_fallback = fallback
            self.compiler = self.compiler_factory(self.plan.name)
            result = self.optional_result()
            return self.finish(result, hook, inline=True)
        return fallback

    def can_inline_optional(self):
        return (
            self.compiler.has_validated_object_header
            and self.has_flat_dict_fields()
            and all(param.kind == ParamKind.POS_OR_KW for param in self.plan.shape.params)
            and all(
                field.is_required or isinstance(field.default, (DefaultValue, DefaultFactory))
                for field in self.plan.shape.fields
            )
        )

    def has_flat_dict_fields(self):
        crown = self.plan.name_layout.crown
        return (
            isinstance(crown, InpDictCrown) and crown.extra_policy == ExtraSkip()
            and self.plan.name_layout.extra_move is None and not self.plan.skipped_fields
            and len(crown.map) == len(self.plan.shape.fields) and bool(crown.map)
            and all(isinstance(child, InpFieldCrown) for child in crown.map.values())
            and len({child.id for child in crown.map.values()}) == len(self.plan.shape.fields)
        )

    def optional_result(self):
        c = self.compiler
        generic, done = c.label("optional_model_slow"), c.label("optional_model_done")
        result = c.slot(owned=True)
        c.branch_if_type(c.data, dict, generic, invert=True)
        crown = self.plan.name_layout.crown
        state = (
            c.constant(None) if self.plan.debug_trail == DebugTrail.DISABLE else
            c.lazy_call(partial(runtime.LoadState, self.plan.debug_trail, self.plan.model_identity))
        )
        required_keys = frozenset(
            key for key, child in crown.map.items() if self.plan.shape.fields_dict[child.id].is_required
        )
        exact_dict = c.dictionary_guard(c.data)
        first = self.field_ir.operations[0]
        fields = (
            self.emit_fields((first,), state, fallback_label=generic) if isinstance(first, ReadScalarFields) else {}
        )
        for index, (key, child) in enumerate(list(crown.map.items())[len(fields):], start=len(fields)):
            field = self.plan.shape.fields_dict[child.id]
            raw = (
                c.guarded_get_item(
                    c.data, key, exact_dict,
                    partial(runtime.handle_flat_load_access_error, required_keys, key, first=index == 0), state, c.data,
                ) if field.is_required else c.dict_lookup(c.data, key, runtime.MISSING)
            )
            skip = c.label("omitted_field")
            c.branch_if(raw, runtime.MISSING, skip)
            loader = self.plan.field_loaders[field.id]
            self.convert_in_place(loader, raw, (key,), state)
            if field.is_optional and self.plan.props.use_default_for_omitted:
                converted_done = c.label("explicit_field_ready")
                c.asm.jump(converted_done)
                c.asm.label(skip)
                c.release(raw, retained=True)
                default = (
                    c.call(field.default.factory) if isinstance(field.default, DefaultFactory) else
                    c.new_reference(field.default.value)
                )
                c.transfer(default, raw)
                c.asm.label(converted_done)
            else:
                c.asm.label(skip)
            fields[field.id] = raw
        if self.plan.debug_trail != DebugTrail.DISABLE:
            c.finish_lazy_state(state, runtime.finish_load, "optional_model_valid")
        args = tuple(fields[param.field_id] for param in self.plan.shape.params)
        value = c.construct_object(
            self.plan.shape.constructor, args, (), tuple(param.name for param in self.plan.shape.params),
            steal=True, omitted=None if self.plan.props.use_default_for_omitted else runtime.MISSING,
        )
        c.transfer(value, result)
        for value in fields.values():
            c.release(value)
        if isinstance(state, Slot):
            c.release(state)
        c.asm.jump(done)
        return c.fallback_result(result, self.flat_fallback, generic, done)

    def can_inline(self) -> bool:
        return self.has_flat_dict_fields() and all(field.is_required for field in self.plan.shape.fields)

    def compile_inline(self, hook: CodeGenHook):
        result = self.inline_result()
        return self.finish(result, hook, inline=True)

    def inline_result(self):
        """Flat required fields need no traversal state, packed dict or argument tuple."""
        c = self.compiler
        crown = self.plan.name_layout.crown
        if not isinstance(crown, InpDictCrown):
            raise TypeError
        state = (
            c.constant(None) if self.plan.debug_trail == DebugTrail.DISABLE else
            c.lazy_call(partial(runtime.LoadState, self.plan.debug_trail, self.plan.model_identity))
        )
        fields = self.emit_fields(self.field_ir.operations, state)
        if self.plan.debug_trail != DebugTrail.DISABLE:
            c.finish_lazy_state(state, runtime.finish_load, "no_load_errors")
        args = tuple(fields[param.field_id] for param in self.plan.shape.params)
        keyword_names = tuple(param.name for param in self.plan.shape.params if param.kind == ParamKind.KW_ONLY)
        result = c.construct_object(
            self.plan.shape.constructor, args, keyword_names, tuple(param.name for param in self.plan.shape.params),
            steal=True,
        )
        for value in fields.values():
            c.release(value)
        if isinstance(state, Slot):
            c.release(state)
        return result

    def emit_fields(
        self, operations: tuple[Operation, ...], state: Slot | Immediate, *, fallback_label: str | None = None,
    ) -> dict[str, Slot]:
        return emit_field_block(
            operations, self.field_ir.required_keys,
            partial(
                X86FieldBackend, self.compiler, state, self.plan.debug_trail, inline_budget=MAX_INLINE_CODE_SIZE,
            ),
            (lambda: self.compiler.asm.jump(fallback_label)) if fallback_label is not None else None,
        )

    def node(self, crown: InpDictCrown | InpListCrown, path: CrownPath, data: Slot) -> Slot:
        c = self.compiler
        required_keys = frozenset(
            key for key, child in crown.map.items()
            if not (isinstance(child, InpFieldCrown) and self.plan.shape.fields_dict[child.id].is_optional)
        ) if isinstance(crown, InpDictCrown) else frozenset()
        spec = runtime.LoadNodeSpec(
            crown=crown,
            path=path,
            required_keys=required_keys,
            strict_coercion=self.plan.strict_coercion,
            collect_extra=self.plan.name_layout.extra_move is not None,
        )
        node = c.call(partial(runtime.enter_load_node, spec), self.state, data)
        data_type = c.call_c("PyObject_Type", data) if isinstance(crown, InpDictCrown) else None
        items = crown.map.items() if isinstance(crown, InpDictCrown) else enumerate(crown.map)
        for key, child in items:
            if isinstance(child, InpNoneCrown):
                continue
            field = self.plan.shape.fields_dict[child.id] if isinstance(child, InpFieldCrown) else None
            read = partial(runtime.read_load_value, key, field, use_default=self.plan.props.use_default_for_omitted)
            if data_type is None:
                raw = c.call(read, self.state, node)
            else:
                raw = self.dict_read(data, data_type, node, key, read)
            if field is not None:
                self.convert(field, (*path, key), raw)
            else:
                if not isinstance(child, (InpDictCrown, InpListCrown)):
                    raise TypeError(f"Unknown input crown: {child}")
                skip = c.label("absent_node")
                c.branch_if(raw, runtime.MISSING, skip)
                child_node = self.node(child, (*path, key), raw)
                self.discard(partial(runtime.attach_load_extra, key), node, child_node)
                c.release(child_node)
                c.asm.label(skip)
            c.release(raw)
        self.discard(runtime.leave_load_node, self.state, node)
        if data_type is not None:
            c.release(data_type)
        return node

    def dict_read(self, data: Slot, data_type: Slot, node: Slot, key: str | int, read) -> Slot:
        c = self.compiler
        result = c.slot(owned=True)
        exact, fallback, done = c.label("exact_dict"), c.label("mapping_fallback"), c.label("raw_ready")
        c.branch_if(data_type, dict, exact)
        c.asm.jump(fallback)
        c.asm.label(exact)
        value = c.dict_lookup(data, key, runtime.MISSING)
        c.branch_if(value, runtime.MISSING, fallback)
        c.transfer(value, result)
        c.asm.jump(done)
        c.asm.label(fallback)
        fallback_value = c.call(read, self.state, node)
        c.transfer(fallback_value, result)
        c.asm.label(done)
        c.release(value)
        return result

    def convert(self, field: InputField, path: CrownPath, raw: Slot) -> None:
        c = self.compiler
        skip = c.label("absent_field")
        c.branch_if(raw, runtime.MISSING, skip)
        loader = self.plan.field_loaders[field.id]
        value = raw if loader is as_is_stub else self.apply_loader(loader, raw, path, self.state)
        converted = c.label("failed_conversion")
        c.branch_if(value, runtime.MISSING, converted)
        c.call_c("PyDict_SetItem", self.values, c.constant(field.id), value, result="int")
        c.asm.label(converted)
        if value != raw:
            c.release(value)
        c.asm.label(skip)

    def convert_in_place(self, loader: Loader, raw: Slot, path: CrownPath, state: Slot | Immediate) -> None:
        if loader is not as_is_stub:
            converted = self.apply_loader(loader, raw, path, state)
            if converted != raw:
                self.compiler.release(raw)
                self.compiler.transfer(converted, raw)

    def apply_loader(self, loader: Loader, raw: Slot, path: CrownPath, state: Slot | Immediate) -> Slot:
        c = self.compiler
        expected = next((target for function, target in IDENTITY_LOADERS if loader is function), None)
        if expected is None or not c.has_validated_object_header:
            return self.call_loader(loader, raw, path, state)
        # Strict scalar loaders return exact-type inputs unchanged. Transfer
        # the owned reference, avoiding both a Python call and an incref/decref.
        # Mismatches retain the original converter and its exception behavior.
        fallback, done = c.label("scalar_fallback"), c.label("scalar_ready")
        c.branch_if_type(raw, expected, fallback, invert=True)
        c.asm.jump(done)
        c.asm.label(fallback)
        converted = (
            c.call(loader, raw) if self.plan.debug_trail == DebugTrail.DISABLE else
            c.guarded_call(loader, (raw,), partial(runtime.handle_load_error, path), state)
        )
        c.release(raw)
        c.transfer(converted, raw)
        c.asm.label(done)
        return raw

    def call_loader(self, loader: Loader, raw: Slot, path: CrownPath, state: Slot | Immediate) -> Slot:
        c = self.compiler
        if self.plan.debug_trail == DebugTrail.DISABLE:
            return c.inline_call(loader, raw, code_budget=MAX_INLINE_CODE_SIZE)
        return c.inline_call(
            loader, raw, partial(runtime.handle_load_error, path), state, code_budget=MAX_INLINE_CODE_SIZE,
        )


def merge_constructor_extra(kwargs: dict, extra: dict) -> None:
    duplicates = kwargs.keys() & extra.keys()
    if duplicates:
        key = next(iter(duplicates))
        raise TypeError(f"Constructor got multiple values for keyword argument {key!r}")
    kwargs.update(extra)


class NativeModelDumperGen(NativeModelGen[ModelDumperPlan]):
    def compile(self, hook: CodeGenHook):
        self.compiler = self.compiler_factory(self.plan.name)
        result = self.compile_result()
        crown = self.plan.name_layout.crown
        fusible = (
            isinstance(crown, OutDictCrown)
            and self.plan.name_layout.extra_move is None
            and bool(crown.map)
            and all(
                isinstance(child, OutFieldCrown)
                and isinstance(self.plan.shape.fields_dict[child.id].accessor, DescriptorAccessor)
                for child in crown.map.values()
            )
        )
        return self.finish(result, hook, inline=fusible)

    def compile_result(self):
        c = self.compiler
        self.state = (
            c.constant(None) if self.plan.debug_trail == DebugTrail.DISABLE else
            c.lazy_call(partial(runtime.DumpState, self.plan.debug_trail, self.plan.model_identity), c.data)
        )
        result = self.crown(self.plan.name_layout.crown)
        extra_move = self.plan.name_layout.extra_move
        if isinstance(extra_move, ExtraTargets):
            for field_id in extra_move.fields:
                extra = self.field(self.plan.shape.fields_dict[field_id])
                skip = c.label("absent_extra")
                c.branch_if(extra, runtime.MISSING, skip)
                self.discard(runtime.update_dump_extra, self.state, result, extra)
                c.asm.label(skip)
                c.release(extra)
        elif isinstance(extra_move, ExtraExtract):
            if self.plan.debug_trail == DebugTrail.ALL:
                extra = c.guarded_call(extra_move.func, (c.data,), partial(runtime.handle_dump_error, None), self.state)
            else:
                extra = c.call(extra_move.func, c.data)
            skip = c.label("failed_extractor")
            c.branch_if(extra, runtime.MISSING, skip)
            self.discard(runtime.update_dump_extra, self.state, result, extra)
            c.asm.label(skip)
            c.release(extra)
        if self.plan.debug_trail != DebugTrail.DISABLE:
            c.finish_lazy_state(self.state, runtime.finish_dump, "no_dump_errors")
            if isinstance(self.state, Slot):
                c.release(self.state)
        return result

    def field(self, field: OutputField, sieve=None) -> Slot:
        c = self.compiler
        raw = self.read_field(field)
        dumper = self.plan.fields_dumpers[field.id]
        if sieve is None and dumper is as_is_stub:
            return raw
        if self.plan.debug_trail == DebugTrail.DISABLE and field.is_required and sieve is None:
            result = c.inline_call(dumper, raw)
            c.release(raw)
            return result
        return self.convert_field(field, raw, sieve)

    def read_field(self, field: OutputField) -> Slot:
        c = self.compiler
        accessor = field.accessor
        handler = partial(runtime.handle_dump_access_error, field)
        if self.plan.debug_trail == DebugTrail.DISABLE and field.is_required:
            if isinstance(accessor, DescriptorAccessor):
                raw = c.get_attr(c.data, accessor.attr_name)
            elif isinstance(accessor, ItemAccessor):
                raw = c.call_c("PyObject_GetItem", c.data, c.constant(accessor.key))
            else:
                raw = c.call(accessor.getter, c.data)
        elif isinstance(accessor, DescriptorAccessor):
            raw = c.guarded_get_attr(c.data, accessor.attr_name, handler, self.state)
        elif isinstance(accessor, ItemAccessor):
            raw = c.guarded_c_call("PyObject_GetItem", (c.data, c.constant(accessor.key)), handler, self.state)
        else:
            raw = c.guarded_call(accessor.getter, (c.data,), handler, self.state)
        return raw

    def convert_field(self, field: OutputField, raw: Slot, sieve) -> Slot:
        c = self.compiler
        dumper = self.plan.fields_dumpers[field.id]
        result = c.slot(owned=True)
        skip = c.label("absent_output")
        c.branch_if(raw, runtime.MISSING, skip)
        filtered = None
        if sieve is not None:
            default = get_default_clause(sieve)
            if isinstance(default, DefaultValue) and (default.value is None or type(default.value) is bool):
                c.branch_if(raw, default.value, skip)
            else:
                filtered = c.call(partial(runtime.filter_dump_value, sieve), c.data, raw)
                c.branch_if(filtered, runtime.MISSING, skip)
        else:
            filtered = raw
        if dumper is as_is_stub:
            value = raw
        elif self.plan.debug_trail == DebugTrail.DISABLE:
            value = c.inline_call(dumper, raw)
        else:
            value = c.inline_call(dumper, raw, partial(runtime.handle_dump_error, field), self.state)
        # Transfer ownership to the merged slot. Both arms yield a new reference.
        c.transfer(value, result)
        done = c.label("output_done")
        c.asm.jump(done)
        c.asm.label(skip)
        missing = c.new_reference(runtime.MISSING)
        c.transfer(missing, result)
        c.asm.label(done)
        # A fused model can run repeatedly inside one list traversal. Every
        # filtered reference must be released before its slot is reused.
        if isinstance(filtered, Slot) and filtered != raw:
            c.release(filtered)
        c.release(raw)
        return result

    def put(self, result: Slot, key: str | int, value: Slot, *, is_dict: bool) -> None:
        c = self.compiler
        skip = c.label("skip_output")
        c.branch_if(value, runtime.MISSING, skip)
        if is_dict:
            c.call_c("PyDict_SetItem", result, c.constant(key), value, result="int")
        else:
            c.call_c("PyList_Append", result, value, result="int")
        c.asm.label(skip)
        c.release(value)

    def crown(self, crown: OutCrown) -> Slot:
        c = self.compiler
        if isinstance(crown, OutNoneCrown):
            if isinstance(crown.placeholder, DefaultFactory):
                if self.plan.debug_trail == DebugTrail.ALL:
                    return self.placeholder_factory(crown.placeholder)
                return c.call(crown.placeholder.factory)
            return c.new_reference(crown.placeholder.value)
        if isinstance(crown, OutListCrown):
            result = c.call_c("PyList_New", Immediate(0))
            for key, child in enumerate(crown.map):
                value = (
                    self.field(self.plan.shape.fields_dict[child.id]) if isinstance(child, OutFieldCrown) else
                    self.crown(child)
                )
                self.put(result, key, value, is_dict=False)
            return result
        if not isinstance(crown, OutDictCrown):
            raise TypeError(f"Unknown output crown: {crown}")
        return self.dict_crown(crown)

    def placeholder_factory(self, placeholder: DefaultFactory) -> Slot:
        c = self.compiler
        result = c.new_reference(runtime.MISSING)
        errors = c.call(runtime.dump_has_errors, self.state)
        skip = c.label("skip_placeholder")
        c.branch_if(errors, constant=True, label=skip)
        c.release(result)
        value = c.call(placeholder.factory)
        c.transfer(value, result)
        c.asm.label(skip)
        c.release(errors)
        return result

    def required_values(self, crown: OutDictCrown) -> dict[str, Slot]:
        # Preserve the Python generator's order: required fields and nested
        # structures precede optional and sieved fields at each dictionary node.
        c = self.compiler
        before: dict[str, Slot] = {}
        entries = list(crown.map.items())
        index = 0
        while index < len(entries):
            key, child = entries[index]
            batch = []
            for candidate_key, candidate in entries[index:]:
                if not isinstance(candidate, OutFieldCrown):
                    break
                field = self.plan.shape.fields_dict[candidate.id]
                if (
                    not field.is_required or candidate_key in crown.sieves
                    or not isinstance(field.accessor, DescriptorAccessor)
                    or self.plan.fields_dumpers[field.id] is not as_is_stub
                ):
                    break
                batch.append((candidate_key, field))
            if batch and (len(batch) > 1 or (len(entries) == 1 and not crown.sieves)):
                names = tuple(
                    field.accessor.attr_name for _, field in batch if isinstance(field.accessor, DescriptorAccessor)
                )
                handlers = (
                    () if self.plan.debug_trail == DebugTrail.DISABLE else
                    tuple(partial(runtime.handle_dump_access_error, field) for _, field in batch)
                )
                before.update(zip(
                    (key for key, _ in batch), c.get_attrs(c.data, names, handlers, self.state), strict=True,
                ))
                index += len(batch)
                continue
            if isinstance(child, OutFieldCrown):
                field = self.plan.shape.fields_dict[child.id]
                if field.is_required and key not in crown.sieves:
                    before[key] = self.field(field)
            else:
                before[key] = self.crown(child)
            index += 1
        return before

    def dict_crown(self, crown: OutDictCrown) -> Slot:
        c = self.compiler
        before = self.required_values(crown)
        if len(before) == len(crown.map) and not crown.sieves:
            return self.required_dict(before)
        if before and not any(key in crown.sieves for key in before):
            result = self.required_dict(before)
        else:
            result = c.call_c("PyDict_New")
            for key, value in before.items():
                if key not in crown.sieves:
                    self.put(result, key, value, is_dict=True)
        for key, child in crown.map.items():
            if key in before:
                if key in crown.sieves:
                    value = (
                        c.call(
                            partial(runtime.filter_dump_structure, crown.sieves[key]), self.state, before[key], c.data,
                        )
                        if self.plan.debug_trail == DebugTrail.ALL else
                        c.call(partial(runtime.filter_dump_value, crown.sieves[key]), c.data, before[key])
                    )
                    self.put(result, key, value, is_dict=True)
                    c.release(before[key])
                continue
            if not isinstance(child, OutFieldCrown):
                raise TypeError(f"Unknown output crown: {child}")
            value = self.field(self.plan.shape.fields_dict[child.id], crown.sieves.get(key))
            self.put(result, key, value, is_dict=True)
        return result

    def required_dict(self, values: dict[str, Slot]) -> Slot:
        c = self.compiler
        # Exact string keys cannot invoke user equality or overwrite another
        # entry here. The completed dictionary retains each non-null value.
        if self.plan.debug_trail == DebugTrail.DISABLE:
            result = c.make_dict(values, consume=True)
        else:
            result = c.slot(owned=True)
            failed, done = c.label("partial_dict"), c.label("dict_ready")
            c.branch_if_null(self.state, failed, invert=True)
            complete = c.make_dict(values, consume=True)
            c.transfer(complete, result)
            c.asm.jump(done)
            c.asm.label(failed)
            partial_dict = c.call_c("PyDict_New")
            c.transfer(partial_dict, result)
            for key, value in values.items():
                self.put(result, key, value, is_dict=True)
            c.asm.label(done)
        return result
