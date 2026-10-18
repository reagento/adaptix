from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from adaptix._internal.code_tools.x86_64_assembler import Immediate, Slot
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
from adaptix._internal.common import Loader
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.morphing.model import native_runtime as runtime
from adaptix._internal.morphing.model.crown_definitions import CrownPath
from adaptix._internal.morphing.native.bytecodes import FieldBackend


@dataclass
class X86FieldBackend(FieldBackend[Slot]):
    compiler: X86Compiler
    state: Slot | Immediate
    debug_trail: DebugTrail
    inline_budget: int | None = None
    exact_dict: Slot | None = None
    guarded: bool = False

    def read_required(self, key: str, index: int, required_keys: frozenset[str]) -> Slot:
        c = self.compiler
        if not self.guarded:
            self.exact_dict = c.dictionary_guard(c.data)
            self.guarded = True
        return c.guarded_get_item(
            c.data, key, self.exact_dict,
            partial(runtime.handle_flat_load_access_error, required_keys, key, first=index == 0), self.state, c.data,
        )

    def read_optional(self, key: str) -> Slot:
        return self.compiler.dict_lookup(self.compiler.data, key, runtime.MISSING)

    def when_present(self, value: Slot, body: Callable[[], None]) -> None:
        c = self.compiler
        skip = c.label("missing_inline_field")
        c.branch_if(value, runtime.MISSING, skip)
        body()
        c.asm.label(skip)

    def when_type_mismatch(self, value: Slot, types: tuple[type, ...], body: Callable[[], None]) -> None:
        c = self.compiler
        if not c.has_validated_object_header or not types:
            body()
            return
        fallback, done = c.label("scalar_fallback"), c.label("scalar_ready")
        for cls in types[:-1]:
            c.branch_if_type(value, cls, done)
        c.branch_if_type(value, types[-1], fallback, invert=True)
        c.asm.jump(done)
        c.asm.label(fallback)
        body()
        c.asm.label(done)

    def call_converter(self, converter: Loader, value: Slot, path: CrownPath, *, inline: bool) -> Slot:
        c = self.compiler
        if self.debug_trail == DebugTrail.DISABLE:
            return (
                c.inline_call(converter, value, code_budget=self.inline_budget) if inline else c.call(converter, value)
            )
        handler = partial(runtime.handle_load_error, path)
        return (
            c.inline_call(converter, value, handler, self.state, code_budget=self.inline_budget) if inline else
            c.guarded_call(converter, (value,), handler, self.state)
        )

    def replace(self, value: Slot, replacement: Slot) -> Slot:
        if value != replacement:
            self.compiler.release(value)
            self.compiler.transfer(replacement, value)
        return value

    def read_scalar_fields(
        self, names: tuple[str, ...], types: tuple[tuple[type, ...] | None, ...],
        fallback: Callable[[], list[Slot] | None],
    ) -> list[Slot] | None:
        return self.compiler.get_items(self.compiler.data, names, types, fallback)
