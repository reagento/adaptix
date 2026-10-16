import gc
from dataclasses import dataclass, field, make_dataclass
from types import BuiltinFunctionType
from typing import Any, List

import pytest
from tests_helpers import raises_exc, reference_counts

from adaptix import CodeGenBackend, Retort, loader, name_mapping
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator
from adaptix._internal.morphing.model.dumper_gen import BuiltinModelDumperGen
from adaptix._internal.morphing.model.loader_gen import BuiltinModelLoaderGen
from adaptix._internal.morphing.native.x86_64 import model as native_model


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


@dataclass
class Node:
    value: int
    children: List["Node"] = field(default_factory=list)


def test_native_models_never_generate_python_source(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Python model code generator was called")

    monkeypatch.setattr(BuiltinModelLoaderGen, "produce_code", forbidden)
    monkeypatch.setattr(BuiltinModelDumperGen, "produce_code", forbidden)
    accumulator = CodeGenAccumulator()
    retort = Retort(codegen_backend=CodeGenBackend.X86_64, recipe=[accumulator])
    load = retort.get_loader(Node)
    dump = retort.get_dumper(Node)
    data = {"value": 1, "children": [{"value": 2, "children": []}]}

    assert isinstance(load, BuiltinFunctionType)
    assert isinstance(dump, BuiltinFunctionType)
    assert dump(load(data)) == data
    assert retort.get_loader(Node) is load
    assert retort.get_dumper(Node) is dump
    assert accumulator.list
    for _, generated in accumulator.list:
        assert generated.backend == CodeGenBackend.X86_64
        assert generated.source.startswith(".intel_syntax noprefix")
        assert generated.machine_code
        assert "PyObject_" in generated.source


def test_replace_and_extend_preserve_backend(debug_trail):
    original = Retort(debug_trail=debug_trail)
    original.get_loader(Node)
    retort = original.replace(codegen_backend=CodeGenBackend.X86_64)
    extended = retort.extend(recipe=[loader(int, lambda data: data + 1)])
    data = {"value": 1, "children": [{"value": 2}]}

    assert retort.load(data, Node) == Node(1, [Node(2)])
    assert extended.load(data, Node) == Node(2, [Node(3)])
    assert original.codegen_backend == CodeGenBackend.PYTHON
    assert extended.codegen_backend == CodeGenBackend.X86_64
    restored = extended.replace(codegen_backend=CodeGenBackend.PYTHON)
    assert restored.load(data, Node) == Node(2, [Node(3)])


def test_defaults_and_omit_default(debug_trail):
    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64,
        debug_trail=debug_trail,
        recipe=[name_mapping(omit_default=True)],
    )
    first = retort.load({"value": 1}, Node)
    second = retort.load({"value": 2}, Node)
    first.children.append(second)
    assert second.children == []
    assert retort.dump(first) == {"value": 1, "children": [{"value": 2}]}


def test_generated_functions_outlive_retort():
    retort = Retort(codegen_backend=CodeGenBackend.X86_64)
    load = retort.get_loader(Node)
    dump = retort.get_dumper(Node)
    del retort
    gc.collect()
    for _ in range(100):
        assert dump(load({"value": 1})) == {"value": 1, "children": []}


def test_inlining_reuses_model_ir(monkeypatch):
    @dataclass
    class Child:
        value: int

    @dataclass
    class Parent:
        left: Child
        right: Child

    builds = []
    build = native_model.build_model_fields

    def record(plan):
        builds.append(plan.shape.constructor)
        return build(plan)

    monkeypatch.setattr(native_model, "build_model_fields", record)
    retort = Retort(codegen_backend=CodeGenBackend.X86_64)
    load = retort.get_loader(Parent)
    assert builds.count(Child) == 1
    assert builds.count(Parent) == 1
    child_ir = retort.get_loader(Child).__self__.program.loader_ir
    assert child_ir is not None
    for _ in range(10):
        assert load({"left": {"value": 1}, "right": {"value": 2}}) == Parent(Child(1), Child(2))
    assert builds == [Child, Parent]


@pytest.mark.parametrize("with_default", [False, True])
def test_model_inlining_budget_keeps_container_calls_and_errors(monkeypatch, debug_trail, with_default):
    monkeypatch.setattr(native_model, "MAX_INLINE_CODE_SIZE", 0)
    model = make_dataclass("Model", [
        ("values", list[int], field(default_factory=list) if with_default else field()),
    ])
    python = Retort(debug_trail=debug_trail).get_loader(model)
    native = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail).get_loader(model)
    if isinstance(native, BuiltinFunctionType):
        child = native.__self__.program.plan.field_loaders["values"]
        assert any(constant is child for constant in native.__self__.constants)
    for data in [{"values": [1000, 2000]}, {"values": []}]:
        assert native(data) == python(data)
    if with_default:
        assert native({}) == python({})
    for data in [{"values": [1000, "bad"]}, {"values": None}]:
        with pytest.raises(Exception, match=r".*") as expected:
            python(data)
        raises_exc(expected.value, lambda data=data: native(data))


def test_field_ir_keeps_reads_after_input_finalizers(debug_trail):
    @dataclass
    class Model:
        head: int
        first: object
        second: int

    events = []
    data = {"head": 1, "second": 2}

    class Value:
        def __del__(self):
            events.append("finalize")
            data["second"] = 20

    data["first"] = Value()

    def convert(value):
        events.append("convert")
        del data["first"]
        return 0

    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail, recipe=[loader("first", convert)],
    )
    assert retort.load(data, Model) == Model(1, 0, 20)
    assert events == ["convert", "finalize"]


def test_base_exceptions_are_not_aggregated(debug_trail):
    error = KeyboardInterrupt()

    def interrupt(value):
        raise error

    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64,
        debug_trail=debug_trail,
        recipe=[loader(int, interrupt)],
    )
    with pytest.raises(KeyboardInterrupt) as captured:
        retort.load({"value": 1}, Node)
    assert captured.value is error


def test_unsupported_platform_rejected_at_configuration(monkeypatch):
    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.platform.machine", lambda: "aarch64")
    with pytest.raises(RuntimeError, match="Linux x86-64"):
        Retort(codegen_backend=CodeGenBackend.X86_64)
    with pytest.raises(RuntimeError, match="Linux x86-64"):
        Retort().replace(codegen_backend=CodeGenBackend.X86_64)
    assert Retort().load(1, int) == 1


def test_invalid_backend_rejected():
    with pytest.raises(ValueError, match="CodeGenBackend"):
        Retort(codegen_backend="unknown")


class IntSubclass(int):
    pass


class StrSubclass(str):
    __slots__ = ()


class FloatSubclass(float):
    pass


@pytest.mark.parametrize(
    ["target", "data", "expected"],
    [(int, 1000, 1000), (str, "value", "value"), (bool, True, True), (float, 1.5, 1.5), (float, 3, 3.0)],
)
def test_strict_scalar_fast_paths(debug_trail, target, data, expected):
    model = make_dataclass("Scalar", [("value", target)])
    retort = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail)
    result = retort.load({"value": data}, model)
    assert result == model(expected)
    assert type(result.value) is target
    if type(data) is target:
        assert result.value is data


@pytest.mark.parametrize(
    ["target", "data"],
    [(int, True), (int, IntSubclass(1)), (str, StrSubclass("a")), (bool, 1),
     (float, True), (float, FloatSubclass(1.0)), (float, 10 ** 1000)],
)
def test_scalar_fallback_preserves_python_errors(debug_trail, target, data):
    model = make_dataclass("Scalar", [("value", target)])
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    with pytest.raises(Exception, match=r".") as reference:
        python.load({"value": data}, model)
    raises_exc(reference.value, lambda: native.load({"value": data}, model))


def test_scalar_fast_path_keeps_custom_loader(debug_trail):
    class CustomLoader:
        def __init__(self):
            self.calls = []

        def __call__(self, value):
            self.calls.append(value)
            return value + 1

    convert = CustomLoader()
    model = make_dataclass("Scalar", [("value", int)])
    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail,
        recipe=[loader(int, convert)],
    )
    assert retort.load({"value": 10}, model) == model(11)
    assert convert.calls == [10]


@pytest.mark.parametrize("with_default", [False, True])
def test_unvalidated_object_header_uses_c_api(monkeypatch, debug_trail, with_default):
    monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.inline_refcount_mode", lambda: None)
    model = make_dataclass("Scalar", [("value", int, field(default=1000) if with_default else field())])
    retort = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail)
    assert retort.load({"value": 1000}, model) == model(1000)
    if with_default:
        assert retort.load({}, model) == model(1000)


def test_dictionary_cache_observes_mutations_from_an_earlier_field_loader(debug_trail):
    @dataclass
    class Model:
        first: int
        second: int

    data = {"first": 1, "second": 2}

    def mutate(value):
        data.clear()
        data.update({"other": 3, "second": value + 10, "first": value})
        return value

    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail,
        recipe=[loader("first", mutate)],
    )
    load = retort.get_loader(Model)
    assert load(data) == Model(1, 11)
    data.clear()
    data.update(first=2, second=0)
    assert load(data) == Model(2, 12)


def test_scalar_prefix_keeps_later_reads_after_custom_loaders(debug_trail):
    @dataclass
    class Model:
        first: int | str
        second: str | None
        third: int
        last: str = "default"

    data = {"first": 1, "second": None, "third": 3, "last": "old"}
    seen = []

    def mutate(value):
        seen.append(value)
        data.clear()
        data.update(third=value, first=1, second=None, last="new")
        return value

    load = Retort(
        codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail,
        recipe=[loader("third", mutate)],
    ).get_loader(Model)
    for _ in range(20):
        assert load(data) == Model(1, None, 3, "new")
    assert seen == [3] * 20


@pytest.mark.parametrize("validated_header", [False, True])
def test_union_check_after_custom_loader_preserves_identity_and_errors(monkeypatch, debug_trail, validated_header):
    if not validated_header:
        monkeypatch.setattr("adaptix._internal.code_tools.x86_64_compiler.inline_refcount_mode", lambda: None)

    @dataclass
    class Model:
        first: object
        second: int | str | None

    data = {}
    value = None

    def mutate(first):
        data["second"] = value
        return first

    python = Retort(debug_trail=debug_trail, recipe=[loader("first", mutate)]).get_loader(Model)
    native = Retort(
        debug_trail=debug_trail, recipe=[loader("first", mutate)], codegen_backend=CodeGenBackend.X86_64,
    ).get_loader(Model)
    for value in [1000, "value", None]:
        data.update(first="first", second=object())
        result = native(data)
        assert result == python(data)
        assert result.second is value
    for value in [True, [], IntSubclass(1), StrSubclass("a")]:
        data.update(first="first", second=object())
        with pytest.raises(Exception, match=r".*") as expected:
            python(data)
        raises_exc(expected.value, lambda: native(data))
        assert data["second"] is value


def test_scalar_prefix_fallback_preserves_full_model_errors(debug_trail):
    @dataclass
    class Model:
        first: int | str
        second: str | None
        third: int
        last: str = "default"

    python = Retort(debug_trail=debug_trail).get_loader(Model)
    native = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail).get_loader(Model)
    for _ in range(20):
        for data in [{}, {"first": [], "second": object()}, {"first": 1, "second": None, "third": "bad"}]:
            with pytest.raises(Exception, match=r".*") as expected:
                python(data)
            raises_exc(expected.value, lambda data=data: native(data))
        for data in [{"first": 1, "second": None, "third": 3}, {"first": "a", "second": "b", "third": 3}]:
            assert native(data) == python(data)


def test_dictionary_rows_preserve_errors_and_references_after_partial_validation(debug_trail):
    @dataclass
    class Model:
        first: Any
        second: str
        third: int
        last: float

    python = Retort(debug_trail=debug_trail).get_loader(Model)
    native = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail).get_loader(Model)
    value = object()
    ordered = {"first": value, "second": "value", "third": 3, "last": 1.5}
    deleted = dict(ordered)
    del deleted["second"]
    deleted["extra"] = None
    cases = [
        ordered, dict(reversed(list(ordered.items()))), deleted,
        {**ordered, "last": "invalid"}, {**ordered, "last": 2},
        {key.encode().decode(): item for key, item in ordered.items()},
    ]
    references = reference_counts([value])
    for _ in range(20):
        for data in cases:
            try:
                expected = python(data)
            except Exception as error:
                raises_exc(error, lambda data=data: native(data))
            else:
                assert native(data) == expected
                del expected
    assert reference_counts([value]) == references


@pytest.mark.parametrize("alias", ["x" * size for size in (1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33)] + ["ключ", "x\0key"])
def test_dictionary_rows_match_fresh_aliases_and_reject_same_length_different_keys(alias):
    @dataclass
    class Model:
        first: int
        second: str

    retort = Retort(recipe=[name_mapping(Model, map={"first": alias})])
    python = retort.get_loader(Model)
    native = retort.replace(codegen_backend=CodeGenBackend.X86_64).get_loader(Model)
    for _ in range(20):
        data = {alias.encode().decode(): 42, "second": "value"}
        assert native(data) == python(data)
        bad = {alias[:-1] + "z": 42, "second": "value"}
        with pytest.raises(Exception, match=r".+") as reference:
            python(bad)
        raises_exc(reference.value, lambda bad=bad: native(bad))
