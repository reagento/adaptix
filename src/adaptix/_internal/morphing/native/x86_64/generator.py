from collections.abc import Callable
from dataclasses import dataclass
from types import BuiltinFunctionType
from typing import Any

from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform
from adaptix._internal.common import Dumper, Loader
from adaptix._internal.definitions import CodeGenBackend
from adaptix._internal.morphing.concrete_provider import none_loader
from adaptix._internal.morphing.model.basic_gen import CodeGenHook
from adaptix._internal.morphing.native.codegen import NativeCodeGenerator, publish
from adaptix._internal.morphing.native.plan import (
    DictPlan,
    IterablePlan,
    ModelDumperPlan,
    ModelLoaderPlan,
    NativePlan,
    ScalarPlan,
    TuplePlan,
    UnionPlan,
)
from adaptix._internal.morphing.native.x86_64.dict import build_dict_program
from adaptix._internal.morphing.native.x86_64.iterable import build_list_program
from adaptix._internal.morphing.native.x86_64.model import NativeModelDumperGen, NativeModelLoaderGen
from adaptix._internal.morphing.native.x86_64.scalar import get_program
from adaptix._internal.morphing.native.x86_64.set import build_set_program
from adaptix._internal.morphing.native.x86_64.tuple import build_tuple_program
from adaptix._internal.morphing.native.x86_64.union import build_union_program
from adaptix._internal.retort.operating_retort import FuncWrapper

BUILDERS: dict[type, Callable[..., Any]] = {
    DictPlan: build_dict_program,
    TuplePlan: build_tuple_program,
    UnionPlan: build_union_program,
}


def build_container_program(plan: IterablePlan | DictPlan | TuplePlan | UnionPlan, compiler: X86Compiler):
    if isinstance(plan, IterablePlan):
        builder = build_set_program if plan.origin in (set, frozenset) else build_list_program
        return builder(plan, compiler)
    return BUILDERS[type(plan)](plan, compiler)


@dataclass(frozen=True)
class X86CodeGenerator(NativeCodeGenerator):
    compiler_factory: Callable[[str], X86Compiler] = X86Compiler

    @staticmethod
    def check_platform() -> None:
        check_native_platform()

    def make_compiler(self, name: str) -> X86Compiler:
        compiler = self.compiler_factory(name)
        compiler.program_resolver = get_program
        compiler.callable_wrapper_type = FuncWrapper
        return compiler

    def compile(self, plan: NativePlan, *, hook: CodeGenHook) -> Loader | Dumper:  # noqa: PLR0911
        if isinstance(plan, ModelLoaderPlan):
            return NativeModelLoaderGen(plan, self.make_compiler).compile(hook)
        if isinstance(plan, ModelDumperPlan):
            return NativeModelDumperGen(plan, self.make_compiler).compile(hook)
        if isinstance(plan, ScalarPlan):
            mapper = plan.mapper
            if mapper is none_loader or (
                type(mapper) is BuiltinFunctionType and isinstance(mapper.__self__, NativeCode)
            ):
                return mapper
            program = get_program(mapper)
            if program is None:
                return mapper
            compiler = self.make_compiler(plan.name)
            if not compiler.has_validated_object_header:
                return mapper
        else:
            compiler = self.make_compiler(plan.name)
            program = build_container_program(plan, compiler)
            if program is None:
                return plan.fallback
        return publish(compiler.finish(program.emit(compiler), program=program), hook, CodeGenBackend.X86_64)


X86_64_CODEGEN = X86CodeGenerator()
