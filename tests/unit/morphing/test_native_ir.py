from collections import UserDict
from itertools import product

import pytest

from adaptix._internal.morphing.concrete_provider import int_strict_coercion_loader, str_strict_coercion_loader
from adaptix._internal.morphing.model import native_runtime as runtime
from adaptix._internal.morphing.native.bytecodes import (
    CheckType,
    ConvertField,
    FieldBlock,
    ReadField,
    ReadScalarFields,
    emit_field_block,
)
from adaptix._internal.morphing.native.optimizer import fuse_scalar_reads


class PythonFieldBackend:
    def __init__(self, data):
        self.data = data

    def read_required(self, key, index, required_keys):
        return self.data[key]

    def read_optional(self, key):
        return self.data.get(key, runtime.MISSING)

    def when_present(self, value, body):
        if value is not runtime.MISSING:
            body()

    def when_type_mismatch(self, value, types, body):
        if type(value) not in types:
            body()

    def call_converter(self, converter, value, path, *, inline):
        return converter(value)

    def replace(self, value, replacement):
        return replacement

    def read_scalar_fields(self, names, types, fallback):
        if type(self.data) is not dict or any(type(key) is not str for key in self.data):
            return fallback()
        row = []
        for key, expected in zip(names, types, strict=True):
            if key not in self.data or (expected is not None and type(self.data[key]) not in expected):
                return fallback()
            row.append(self.data[key])
        return row


def execute(block, data):
    return emit_field_block(block.operations, block.required_keys, lambda: PythonFieldBackend(data))


def make_input(input_kind, calls):
    data = {"first": 1, "second": 2, "third": 3}
    if input_kind == "wrong_type":
        data["second"] = "bad"
    elif input_kind == "missing":
        del data["second"]
    elif input_kind == "mapping":
        class Mapping(UserDict):
            def __getitem__(self, key):
                calls.append(("read", key))
                return super().__getitem__(key)

        return Mapping(data)
    return data


def evaluate(kinds, input_kind, defer_last, *, optimized):
    calls = []
    data = make_input(input_kind, calls)

    def convert(value):
        calls.append(("convert", value))
        data["second"] = 20
        data["third"] = 30
        return value

    operations = []
    for index, (key, kind) in enumerate(zip(["first", "second", "third"], kinds, strict=True)):
        operations.append(ReadField(key, key, required=True, index=index))
        if kind == "int":
            operations.append(CheckType(key, (int,), int_strict_coercion_loader, (key,)))
        elif kind == "custom":
            operations.append(ConvertField(key, convert, (key,)))
    block = FieldBlock(tuple(operations), frozenset(data))
    if optimized:
        block = fuse_scalar_reads(block, defer_last=defer_last)
        assert fuse_scalar_reads(block, defer_last=defer_last) is block
    try:
        outcome = execute(block, data)
    except Exception as error:
        outcome = (type(error), str(error))
    return outcome, calls


@pytest.mark.parametrize("kinds", list(product(["identity", "int", "custom"], repeat=3)))
@pytest.mark.parametrize("input_kind", ["valid", "wrong_type", "missing", "mapping"])
@pytest.mark.parametrize("defer_last", [False, True])
def test_fusion_preserves_values_errors_and_callback_order(kinds, input_kind, defer_last):
    assert evaluate(kinds, input_kind, defer_last, optimized=True) == evaluate(
        kinds, input_kind, defer_last, optimized=False,
    )


def test_fusion_keeps_optional_reads_and_nullable_checks():
    block = FieldBlock(
        (
            ReadField("first", "renamed", required=True, index=0),
            CheckType("first", (str, type(None)), str_strict_coercion_loader, ("renamed",)),
            ReadField("second", "second", required=False, index=1),
            CheckType("second", (int,), int_strict_coercion_loader, ("second",)),
        ),
        frozenset({"renamed"}),
    )
    optimized = fuse_scalar_reads(block, defer_last=True)
    assert isinstance(optimized.operations[0], ReadScalarFields)
    assert optimized.operations[0].types == ((str, type(None)),)
    assert optimized.operations[1:] == block.operations[2:]
    assert execute(optimized, {"renamed": None, "second": 1}) == {"first": None, "second": 1}


@pytest.mark.parametrize("optimized", [False, True])
@pytest.mark.parametrize("value", [None, "text", 1, True])
def test_exact_type_check_retains_values_or_calls_original_loader(optimized, value):
    calls = []

    def convert(value):
        calls.append(value)
        return "converted"

    block = FieldBlock(
        (
            ReadField("field", "key", required=True, index=0),
            CheckType("field", (int, str, type(None)), convert, ("key",)),
        ),
        frozenset({"key"}),
    )
    if optimized:
        block = fuse_scalar_reads(block)
    result = execute(block, {"key": value})
    if type(value) in (int, str, type(None)):
        assert result["field"] is value
        assert calls == []
    else:
        assert result["field"] == "converted"
        assert calls == [value]


@pytest.mark.parametrize("operation", [CheckType, ConvertField])
def test_missing_optional_field_skips_converter(operation):
    def convert(value):
        pytest.fail("A missing optional field must not call its converter")

    conversion = (
        CheckType("field", (int,), convert, ("key",)) if operation is CheckType else
        ConvertField("field", convert, ("key",))
    )
    block = FieldBlock((ReadField("field", "key", required=False, index=0), conversion), frozenset())
    assert execute(block, {}) == {"field": runtime.MISSING}


@pytest.mark.parametrize("unsupported", [False, True])
def test_scalar_batch_fallback_reads_generic_mapping_once_in_source_order(unsupported):
    calls = []

    class Mapping(UserDict):
        def __getitem__(self, key):
            calls.append(key)
            return super().__getitem__(key)

    class UnsupportedBatchBackend(PythonFieldBackend):
        def read_scalar_fields(self, names, types, fallback):
            return None

    block = fuse_scalar_reads(FieldBlock(
        tuple(ReadField(key, key, required=True, index=index) for index, key in enumerate(("a", "b"))),
        frozenset({"a", "b"}),
    ))
    data = Mapping(a=1, b=2)
    backend = UnsupportedBatchBackend if unsupported else PythonFieldBackend
    assert emit_field_block(block.operations, block.required_keys, lambda: backend(data)) == {"a": 1, "b": 2}
    assert calls == ["a", "b"]


def test_failed_scalar_batch_delegates_to_whole_model_fallback():
    fallbacks = []
    block = fuse_scalar_reads(FieldBlock(
        (ReadField("field", "key", required=True, index=0),), frozenset({"key"}),
    ))
    result = emit_field_block(
        block.operations, block.required_keys, lambda: PythonFieldBackend({}), lambda: fallbacks.append("model"),
    )
    assert result == {}
    assert fallbacks == ["model"]
