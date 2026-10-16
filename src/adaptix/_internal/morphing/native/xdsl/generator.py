import _abc
import ctypes
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import BuiltinFunctionType

from xdsl.dialects import builtin, llvm

from adaptix._internal.code_tools.compiler import BasicClosureCompiler
from adaptix._internal.code_tools.native_access import GENERIC_GETTER, LOOKUP, get_type_version, member_offset, pointer
from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.common import Dumper, Loader
from adaptix._internal.definitions import CodeGenBackend
from adaptix._internal.model_tools.definitions import DescriptorAccessor, ParamKind
from adaptix._internal.morphing.model.basic_gen import CodeGenHook, compile_closure_with_globals_capturing
from adaptix._internal.morphing.model.crown_definitions import (
    ExtraForbid,
    ExtraSkip,
    InpDictCrown,
    OutDictCrown,
    OutFieldCrown,
)
from adaptix._internal.morphing.model.dumper_gen import BuiltinModelDumperGen
from adaptix._internal.morphing.model.loader_gen import BuiltinModelLoaderGen
from adaptix._internal.morphing.native.bytecodes import CheckType, ConvertField, FieldBlock, ReadField
from adaptix._internal.morphing.native.codegen import publish
from adaptix._internal.morphing.native.descriptions import ScalarProgram
from adaptix._internal.morphing.native.model_ir import build_model_fields
from adaptix._internal.morphing.native.plan import (
    IterablePlan,
    ModelDumperPlan,
    ModelLoaderPlan,
    NativePlan,
    ScalarPlan,
)
from adaptix._internal.morphing.native.registry import get_program, identity_spec
from adaptix._internal.morphing.native.xdsl.compiler import PTR, LLVMCode, OwnedValue, XDSLCompiler
from adaptix._internal.special_cases_optimization import as_is_stub
from adaptix._internal.type_tools import strip_alias


class UnsupportedPlan(Exception):
    pass


def model_fallback(plan: ModelLoaderPlan | ModelDumperPlan) -> Loader | Dumper:
    generator: BuiltinModelLoaderGen | BuiltinModelDumperGen
    if isinstance(plan, ModelLoaderPlan):
        generator = BuiltinModelLoaderGen(
            shape=plan.shape,
            name_layout=plan.name_layout,
            debug_trail=plan.debug_trail,
            strict_coercion=plan.strict_coercion,
            field_loaders=plan.field_loaders,
            skipped_fields=plan.skipped_fields,
            model_identity=plan.model_identity,
            props=plan.props,
        )
    else:
        generator = BuiltinModelDumperGen(
            shape=plan.shape,
            name_layout=plan.name_layout,
            debug_trail=plan.debug_trail,
            fields_dumpers=plan.fields_dumpers,
            model_identity=plan.model_identity,
        )
    source, namespace = generator.produce_code(plan.name)
    return compile_closure_with_globals_capturing(
        BasicClosureCompiler(),
        lambda data: None,
        namespace,
        closure_name=plan.name,
        closure_code=source,
        file_name=plan.name,
    )


def mapping_guard(c: XDSLCompiler) -> None:
    if issubclass(list, Mapping) or c.layout.abc_invalidation_counter is None:
        raise UnsupportedPlan
    get_state = ctypes.pythonapi.PyModule_GetState
    get_state.argtypes, get_state.restype = (ctypes.py_object,), ctypes.c_void_p
    state = get_state(_abc)
    expected = _abc.get_cache_token()
    offset = c.layout.abc_invalidation_counter
    if not state or ctypes.c_ssize_t.from_address(state + offset).value != expected:
        raise UnsupportedPlan
    c.constants.append(_abc)
    actual = c.load(c.address(state), offset, builtin.i64)
    c.guard(c.compare(actual, c.integer(expected)))


def compile_scalar(c: XDSLCompiler, program: ScalarProgram) -> OwnedValue:
    c.check_type(c.data, (*program.types, type(None)) if program.nullable else program.types)
    return c.keep(c.data)


def compile_list(c: XDSLCompiler, plan: IterablePlan) -> OwnedValue:
    spec = identity_spec(plan.mapper)
    if plan.origin is not list or plan.dump_as is not list or spec is None:
        raise UnsupportedPlan
    types, nullable = spec
    c.check_type(c.data, (list,))
    if plan.loading and plan.strict_coercion:
        mapping_guard(c)
    size = c.load(c.data, c.layout.var_size, builtin.i64)
    result = c.checked("PyList_New", size)
    # Allocation can trigger GC and change input. Match the existing guarded
    # copy path: use fresh storage and fall back when the input has grown.
    actual = c.load(c.data, c.layout.var_size, builtin.i64)
    c.guard(c.compare(size, actual, "uge"))
    source = c.load(c.data, c.layout.list_items)
    target = c.load(c.value(result), c.layout.list_items)
    loop, finished = c.new_block(builtin.i64), c.new_block()
    c.add(llvm.BrOp(loop, c.zero))
    c.block = loop
    index = loop.args[0]
    body = c.new_block()
    c.add(llvm.CondBrOp(c.compare(index, actual, "ult"), body, [], finished, []))
    c.block = body
    item = c.emit(llvm.LoadOp(c.gep(source, index, PTR), PTR))
    c.check_type(item, (*types, type(None)) if nullable else types)
    c.incref(item)
    c.add(llvm.StoreOp(item, c.gep(target, index, PTR)))
    next_index = c.emit(llvm.AddOp(index, c.one))
    c.add(llvm.BrOp(loop, next_index))
    c.block = finished
    c.add(llvm.StoreOp(actual, c.gep(c.value(result), c.layout.var_size)))
    return result


def model_loader_fields(plan: ModelLoaderPlan) -> FieldBlock:
    if not isinstance(plan.name_layout.crown, InpDictCrown) or plan.name_layout.extra_move is not None:
        raise UnsupportedPlan
    try:
        ir = build_model_fields(plan)
    except TypeError:
        raise UnsupportedPlan from None
    if any(isinstance(op, ConvertField) or (isinstance(op, ReadField) and not op.required) for op in ir.operations):
        raise UnsupportedPlan
    if plan.skipped_fields or any(param.kind is ParamKind.KW_ONLY for param in plan.shape.params):
        raise UnsupportedPlan
    crown = plan.name_layout.crown
    if not isinstance(crown.extra_policy, (ExtraSkip, ExtraForbid)):
        raise UnsupportedPlan
    return ir


def compile_model_loader(c: XDSLCompiler, plan: ModelLoaderPlan) -> OwnedValue:
    ir = model_loader_fields(plan)
    crown = plan.name_layout.crown
    dict_keys, keys_kind, dict_used = c.layout.dict_keys, c.layout.keys_kind, c.layout.dict_used
    if dict_keys is None or keys_kind is None or dict_used is None:
        raise UnsupportedPlan
    c.check_type(c.data, (dict,))
    keys = c.load(c.data, dict_keys)
    c.guard(c.compare(c.load(keys, keys_kind, builtin.i8), c.integer(1, builtin.i8)))
    if isinstance(crown.extra_policy, ExtraForbid):
        c.guard(c.compare(c.load(c.data, dict_used, builtin.i64), c.integer(len(ir.required_keys))))
    values = {}
    for op in ir.operations:
        if isinstance(op, ReadField):
            hash(op.key)
            value = c.call("PyDict_GetItemWithError", c.data, c.pointer(op.key))
            values[op.target] = value
            present = c.compare(value, c.null, "ne")
            missing = c.new_block()
            c.guard(present, missing)
            previous = c.block
            c.block = missing
            error = c.call("PyErr_Occurred")
            c.add(llvm.CondBrOp(c.compare(error, c.null), c.fallback, [], c.error, []))
            c.block = previous
        elif isinstance(op, CheckType):
            c.check_type(values[op.target], op.types)
    arguments = [values[param.field_id] for param in plan.shape.params]
    for argument in arguments:
        c.keep(argument)
    array = c.storage(PTR, len(arguments))
    for index, argument in enumerate(arguments):
        c.add(llvm.StoreOp(argument, c.gep(array, index, PTR)))
    return c.checked("PyObject_Vectorcall", c.pointer(plan.shape.constructor), array, c.integer(len(arguments)), c.null)


def compile_model_dumper(c: XDSLCompiler, plan: ModelDumperPlan) -> OwnedValue:  # noqa: C901
    cls = strip_alias(plan.model_type)
    crown = plan.name_layout.crown
    if (
        not isinstance(cls, type)
        or not isinstance(crown, OutDictCrown)
        or plan.name_layout.extra_move is not None
        or crown.sieves
    ):
        raise UnsupportedPlan
    getattro, type_version = c.layout.type_getattro, c.layout.type_version
    if getattro is None or type_version is None:
        raise UnsupportedPlan
    if pointer(id(cls) + getattro) != GENERIC_GETTER:
        raise UnsupportedPlan
    fields = []
    for key, child in crown.map.items():
        if not isinstance(child, OutFieldCrown):
            raise UnsupportedPlan
        fld = plan.shape.fields_dict[child.id]
        if (
            not fld.is_required
            or not isinstance(fld.accessor, DescriptorAccessor)
            or plan.fields_dumpers[fld.id] is not as_is_stub
        ):
            raise UnsupportedPlan
        try:
            descriptor = LOOKUP(cls, fld.accessor.attr_name)
        except ValueError:
            raise UnsupportedPlan from None
        offset = member_offset(descriptor, cls.__basicsize__)
        if offset is None:
            raise UnsupportedPlan
        fields.append((key, offset))
    version = get_type_version(cls)
    if not version:
        raise UnsupportedPlan
    c.check_type(c.data, (cls,))
    c.guard(c.compare(c.load(c.pointer(cls), type_version, builtin.i32), c.integer(version, builtin.i32)))
    values = []
    for key, offset in fields:
        value = c.load(c.data, offset)
        c.guard(c.compare(value, c.null, "ne"))
        values.append((key, value))
    for value in (value for key, value in values):
        c.keep(value)
    result = c.checked("PyDict_New")
    for key, value in values:
        hash(key)
        status = c.call("PyDict_SetItem", c.value(result), c.pointer(key), value, result=builtin.i32)
        c.guard(c.compare(status, c.integer(0, builtin.i32)), c.error)
    return result


@dataclass(eq=False)
class XDSLCodeGenerator:
    opt_level: int = 2
    canonicalize: bool = True
    capture_artifacts: bool = False
    codes: list[LLVMCode] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)

    def compile(self, plan: NativePlan, *, hook: CodeGenHook) -> Loader | Dumper:
        if (
            isinstance(plan, ScalarPlan) and type(plan.mapper) is BuiltinFunctionType
            and isinstance(plan.mapper.__self__, NativeCode)
        ):
            return plan.mapper
        fallback = model_fallback(plan) if isinstance(plan, (ModelLoaderPlan, ModelDumperPlan)) else plan.fallback
        c = XDSLCompiler(
            plan.name,
            opt_level=self.opt_level,
            canonicalize=self.canonicalize,
            capture_artifacts=self.capture_artifacts,
        )
        program = None
        try:
            if isinstance(plan, ScalarPlan):
                program = get_program(plan.mapper)
                if not isinstance(program, ScalarProgram):
                    raise UnsupportedPlan  # noqa: TRY301
                result = compile_scalar(c, program)
            elif isinstance(plan, IterablePlan):
                result = compile_list(c, plan)
            elif isinstance(plan, ModelLoaderPlan):
                result = compile_model_loader(c, plan)
            elif isinstance(plan, ModelDumperPlan):
                result = compile_model_dumper(c, plan)
            else:
                raise UnsupportedPlan  # noqa: TRY301
        except UnsupportedPlan:
            self.fallbacks.append(plan.name)
            return fallback
        code = c.finish(result, fallback, program=program)
        self.codes.append(code)
        return publish(code, hook, CodeGenBackend.X86_64)
