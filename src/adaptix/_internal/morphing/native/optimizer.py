from dataclasses import replace

from adaptix._internal.morphing.native.bytecodes import (
    CheckType,
    Effect,
    FieldBlock,
    FieldOperation,
    ReadField,
    ReadScalarFields,
)


def fuse_scalar_reads(block: FieldBlock, *, defer_last: bool = False) -> FieldBlock:
    """Fuse a required prefix whose guarded path cannot execute Python.

    A final read can join the batch while its conversion stays after it.
    Reads never cross that conversion, including its decref/finalizer effects.
    """
    operations = block.operations
    reads: list[ReadField] = []
    types: list[tuple[type, ...] | None] = []
    fallback: list[FieldOperation] = []
    cursor = 0
    while cursor < len(operations):
        read = operations[cursor]
        if not isinstance(read, ReadField) or not read.required:
            break
        following = operations[cursor + 1] if cursor + 1 < len(operations) else None
        if following is not None and following.fast_effects & Effect.CALL_PYTHON:
            if defer_last and cursor + 2 == len(operations):
                reads.append(read)
                types.append(None)
                fallback.append(read)
                cursor += 1
            break
        if isinstance(following, CheckType):
            if following.target != read.target or not following.types:
                break
            reads.append(read)
            types.append(following.types)
            fallback.extend((read, following))
            cursor += 2
        elif following is None or isinstance(following, ReadField):
            reads.append(read)
            types.append(None)
            fallback.append(read)
            cursor += 1
        else:
            break
    if not reads:
        return block
    fused = ReadScalarFields(tuple(reads), tuple(types), tuple(fallback))
    return replace(block, operations=(fused, *operations[cursor:]))
