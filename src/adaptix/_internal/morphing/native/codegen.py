from dataclasses import dataclass
from typing import Protocol

from adaptix._internal.common import Dumper, Loader
from adaptix._internal.definitions import CodeGenBackend
from adaptix._internal.morphing.model.basic_gen import CodeGenHook, CodeGenHookData, fetch_code_gen_hook
from adaptix._internal.morphing.native.plan import NativePlan, ScalarPlan
from adaptix._internal.provider.essential import CannotProvide, Mediator
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.located_request import LocatedRequest
from adaptix._internal.utils import AlwaysEqualHashWrapper, IdentityHashWrapper


class NativeCodeGenerator(Protocol):
    def compile(self, plan: NativePlan, *, hook: CodeGenHook) -> Loader | Dumper: ...


@dataclass(frozen=True)
class NativeCodeGenRequest(LocatedRequest[NativeCodeGenerator | None]):
    """Resolve a generator for this location, or None to use Python generation."""


def publish(code, hook: CodeGenHook, backend: CodeGenBackend):
    hook(
        CodeGenHookData(
            namespace={f"constant_{index}": value for index, value in enumerate(code.constants)},
            source=code.assembly,
            backend=backend,
            machine_code=code.machine_code,
        ),
    )
    return code.make_callable()


def fetch_native_codegen(mediator: Mediator, loc_stack: LocStack) -> NativeCodeGenerator | None:
    try:
        return mediator.delegating_provide(NativeCodeGenRequest(loc_stack=loc_stack))
    except CannotProvide:
        return None


def compile_native_scalar(mediator: Mediator, request: LocatedRequest, mapper: Loader | Dumper):
    generator = fetch_native_codegen(mediator, request.loc_stack)
    if generator is None:
        return mapper
    return cached_compile_native(
        mediator, generator, ScalarPlan(mapper=mapper), hook=fetch_code_gen_hook(mediator, request.loc_stack),
    )


def cached_compile_native(
    mediator: Mediator, generator: NativeCodeGenerator, plan: NativePlan, *, hook: CodeGenHook,
) -> Loader | Dumper:
    # Plans contain the resolved converters and settings, rather than just the type.
    # User callables can be unhashable; those remain valid without caching.
    try:
        hash(plan)
    except TypeError:
        return generator.compile(plan, hook=hook)
    return mediator.cached_call(
        compile_native_plan, IdentityHashWrapper(generator), plan, AlwaysEqualHashWrapper(hook),
    )


def compile_native_plan(
    generator: IdentityHashWrapper[NativeCodeGenerator], plan: NativePlan, hook: AlwaysEqualHashWrapper[CodeGenHook],
) -> Loader | Dumper:
    return generator.value.compile(plan, hook=hook.value)


def resolve_native_codegen(backend: CodeGenBackend) -> NativeCodeGenerator | None:
    if backend == CodeGenBackend.PYTHON:
        return None
    if backend == CodeGenBackend.X86_64:
        from adaptix._internal.morphing.native.x86_64.generator import X86_64_CODEGEN  # noqa: PLC0415

        X86_64_CODEGEN.check_platform()
        return X86_64_CODEGEN
    raise ValueError(f"Unsupported CodeGenBackend: {backend}")
