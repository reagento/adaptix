from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Flag, auto
from typing import ClassVar, Generic, Protocol, TypeVar

from adaptix._internal.common import Loader
from adaptix._internal.morphing.model.crown_definitions import CrownPath


class Effect(Flag):
    NONE = 0
    RAISE = auto()
    CALL_PYTHON = auto()


ValueT = TypeVar("ValueT")


class FieldBackend(Protocol[ValueT]):
    """Implement field bodies with runtime values or machine-code slots."""

    def read_required(self, key: str, index: int, required_keys: frozenset[str]) -> ValueT: ...

    def read_optional(self, key: str) -> ValueT: ...

    def when_present(self, value: ValueT, body: Callable[[], None]) -> None: ...

    def when_type_mismatch(self, value: ValueT, types: tuple[type, ...], body: Callable[[], None]) -> None: ...

    def call_converter(self, converter: Loader, value: ValueT, path: CrownPath, *, inline: bool) -> ValueT: ...

    def replace(self, value: ValueT, replacement: ValueT) -> ValueT:
        """Release the old reference and keep its binding valid across branches."""
        ...

    def read_scalar_fields(
        self, names: tuple[str, ...], types: tuple[tuple[type, ...] | None, ...],
        fallback: Callable[[], list[ValueT] | None],
    ) -> list[ValueT] | None:
        """Call fallback on guard failure; return None without calling it if unsupported."""
        ...


class Instruction(Protocol):
    def emit(self, context) -> None: ...


@dataclass
class FieldContext(Generic[ValueT]):
    backend: FieldBackend[ValueT]
    backend_factory: Callable[[], FieldBackend[ValueT]]
    required_keys: frozenset[str]
    model_fallback: Callable[[], None] | None = None
    values: dict[str, ValueT] = field(default_factory=dict)

    def run(self, operations: Sequence[Instruction]) -> dict[str, ValueT]:
        for operation in operations:
            operation.emit(self)
        return self.values

    def child(self):
        return FieldContext(self.backend_factory(), self.backend_factory, self.required_keys)

    def recover(self, operations: Sequence[Instruction]) -> list[ValueT] | None:
        if self.model_fallback is not None:
            self.model_fallback()
            return None
        return list(self.child().run(operations).values())

    def convert(self, target: str, converter: Loader, path: CrownPath, *, inline: bool) -> None:
        value = self.values[target]
        replacement = self.backend.call_converter(converter, value, path, inline=inline)
        self.values[target] = self.backend.replace(value, replacement)


@dataclass(frozen=True, slots=True)
class ReadField:
    """Produce an owned reference, or the missing sentinel, in source order.

    The fast effects apply only to an exact dictionary with verified keys.
    Generic mappings can execute Python, mutate input and raise exceptions.
    """

    target: str
    key: str
    required: bool
    index: int
    owns_result: ClassVar[bool] = True
    effects: ClassVar[Effect] = Effect.RAISE | Effect.CALL_PYTHON
    fast_effects: ClassVar[Effect] = Effect.NONE

    def emit(self, context: FieldContext) -> None:
        context.values[self.target] = (
            context.backend.read_required(self.key, self.index, context.required_keys) if self.required else
            context.backend.read_optional(self.key)
        )


@dataclass(frozen=True, slots=True)
class CheckType:
    """Keep an owned exact-type value; otherwise invoke the original loader."""

    target: str
    types: tuple[type, ...]
    fallback: Loader
    path: CrownPath
    effects: ClassVar[Effect] = Effect.RAISE | Effect.CALL_PYTHON
    fast_effects: ClassVar[Effect] = Effect.NONE

    def emit(self, context: FieldContext) -> None:
        value = context.values[self.target]
        context.backend.when_present(
            value,
            lambda: context.backend.when_type_mismatch(
                value, self.types,
                lambda: context.convert(self.target, self.fallback, self.path, inline=False),
            ),
        )


@dataclass(frozen=True, slots=True)
class ConvertField:
    """Replace an owned value, preserving missing values and error handling.

    Both the call and releasing its input can execute Python, including finalizers.
    """

    target: str
    converter: Loader
    path: CrownPath
    effects: ClassVar[Effect] = Effect.RAISE | Effect.CALL_PYTHON
    fast_effects: ClassVar[Effect] = effects

    def emit(self, context: FieldContext) -> None:
        context.backend.when_present(
            context.values[self.target],
            lambda: context.convert(self.target, self.converter, self.path, inline=True),
        )


FieldOperation = ReadField | CheckType | ConvertField


@dataclass(frozen=True, slots=True)
class ReadScalarFields:
    """Guard and retain a row; failures execute the original operations in order."""

    reads: tuple[ReadField, ...]
    types: tuple[tuple[type, ...] | None, ...]
    fallback: tuple[FieldOperation, ...]
    owns_result: ClassVar[bool] = True
    effects: ClassVar[Effect] = Effect.RAISE | Effect.CALL_PYTHON
    fast_effects: ClassVar[Effect] = Effect.NONE

    def emit(self, context: FieldContext) -> None:
        values = context.backend.read_scalar_fields(
            tuple(read.key for read in self.reads), self.types, lambda: context.recover(self.fallback),
        )
        if values is None:
            if context.model_fallback is None:
                context.values.update(context.child().run(self.fallback))
        else:
            context.values.update((read.target, value) for read, value in zip(self.reads, values, strict=True))


Operation = FieldOperation | ReadScalarFields


@dataclass(frozen=True, slots=True)
class FieldBlock:
    operations: tuple[Operation, ...]
    required_keys: frozenset[str]


def emit_field_block(
    operations: Sequence[Operation], required_keys: frozenset[str],
    backend_factory: Callable[[], FieldBackend[ValueT]], model_fallback: Callable[[], None] | None = None,
) -> dict[str, ValueT]:
    return FieldContext(backend_factory(), backend_factory, required_keys, model_fallback).run(operations)
