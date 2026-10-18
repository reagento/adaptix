import ctypes
import sys
import typing
from dataclasses import dataclass, field
from typing import Literal, Union

import pytest

from adaptix import CodeGenBackend, DebugTrail, P, Retort, bound, dumper, loader
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform
from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator
from adaptix._internal.morphing.native.codegen import NativeCodeGenRequest
from adaptix._internal.morphing.native.plan import (
    DictPlan,
    IterablePlan,
    ModelDumperPlan,
    ModelLoaderPlan,
    ScalarPlan,
    TuplePlan,
    UnionPlan,
)
from adaptix._internal.morphing.native.x86_64.generator import X86CodeGenerator
from adaptix._internal.provider.value_provider import ValueProvider


@dataclass
class Example:
    count: int
    values: list[int]


@dataclass
class FirstVariant:
    kind: Literal["first"]
    value: int


@dataclass
class SecondVariant:
    kind: Literal["second"]
    text: str


@dataclass
class Pair:
    left: Example
    right: Example


@dataclass
class RepeatedContainers:
    left: list[int]
    right: list[int]


@dataclass
class RepeatedOptional:
    left: Example | None
    right: Example | None


@dataclass
class UnhashableLoader:
    offset: int

    def __call__(self, data):
        return data + self.offset


@dataclass
class PortableGenerator:
    """Test backend for plain model fields; containers keep their fallbacks.

    Deliberately unhashable to verify that DI dependencies are cached by identity.
    No instruction encoder or native executable memory is used by this backend.
    """

    offset: int = 0
    calls: list[str] = field(default_factory=list)

    def compile(self, plan, *, hook):
        if isinstance(plan, ModelLoaderPlan):
            self.calls.append("model_loader")

            def load(data):
                result = plan.shape.constructor(
                    **{
                        param.name: plan.field_loaders[param.field_id](data[param.field_id])
                        for param in plan.shape.params
                    },
                )
                if isinstance(result, Example):
                    result.count += self.offset
                return result

            return load
        if isinstance(plan, ModelDumperPlan):
            self.calls.append("model_dumper")
            return lambda data: {
                fld.id: plan.fields_dumpers[fld.id](getattr(data, fld.id)) for fld in plan.shape.fields
            }
        if isinstance(plan, IterablePlan):
            self.calls.append("set" if plan.origin in (set, frozenset) else "list")
        else:
            self.calls.append(
                {ScalarPlan: "scalar", TuplePlan: "tuple", DictPlan: "dict", UnionPlan: "union"}[type(plan)],
            )
        return plan.fallback


def forbid_x86_compilation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Provider bypassed the injected code generator")

    monkeypatch.setattr(X86Compiler, "__init__", forbidden)


def test_all_providers_use_the_injected_generator(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])
    python = Retort()
    cases = [
        (Example, {"count": 1, "values": [2, 3]}),
        (list[int], [1, 2]),
        (tuple[int, str], [1, "text"]),
        (dict[str, int], {"value": 1}),
        (set[int], [1, 2]),
        (Union[FirstVariant, SecondVariant], {"kind": "first", "value": 1}),
    ]
    for tp, data in cases:
        load, dump = retort.get_loader(tp), retort.get_dumper(tp)
        result = load(data)
        assert result == python.load(data, tp)
        assert dump(result) == python.dump(result, tp)
        assert retort.get_loader(tp) is load
        assert retort.get_dumper(tp) is dump
    assert set(generator.calls) == {"model_loader", "model_dumper", "list", "set", "tuple", "dict", "union", "scalar"}

    replaced = retort.replace(debug_trail=DebugTrail.FIRST).extend(recipe=[])
    assert replaced.load(cases[0][1], Example) == Example(1, [2, 3])


def test_located_dependencies_and_cached_models_do_not_share_generators(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    left, right = PortableGenerator(offset=10), PortableGenerator(offset=100)
    retort = Retort(
        recipe=[
            bound(P[Pair].left, ValueProvider(NativeCodeGenRequest, left)),
            bound(P[Pair].right, ValueProvider(NativeCodeGenRequest, right)),
        ],
    )
    item = {"count": 1, "values": [2]}
    assert retort.load({"left": item, "right": item}, Pair) == Pair(Example(11, [2]), Example(101, [2]))
    assert "model_loader" in left.calls
    assert "model_loader" in right.calls


def test_repeated_containers_compile_once_per_direction(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])
    data = {"left": [1], "right": [2]}
    result = retort.load(data, RepeatedContainers)
    assert result == RepeatedContainers([1], [2])
    assert generator.calls.count("list") == 1
    assert retort.dump(result) == data
    assert generator.calls.count("list") == 2


def test_cached_native_plans_preserve_field_specific_converters(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    retort = Retort(recipe=[
        ValueProvider(NativeCodeGenRequest, generator),
        loader(P[RepeatedContainers].left.generic_arg(0, int), lambda data: data + 10),
        loader(P[RepeatedContainers].right.generic_arg(0, int), lambda data: data + 100),
    ])
    assert retort.load({"left": [1], "right": [1]}, RepeatedContainers) == RepeatedContainers([11], [101])
    assert generator.calls.count("list") == 2


def test_cached_scalar_generation_accepts_unhashable_callables(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator), loader(int, UnhashableLoader(10))])
    assert retort.load(1, int) == 11


@pytest.mark.parametrize("use_generator", [False, True])
def test_cached_optional_dumper_accepts_unhashable_callables(monkeypatch, use_generator):
    forbid_x86_compilation(monkeypatch)
    recipe = [dumper(int, UnhashableLoader(10))]
    if use_generator:
        recipe.insert(0, ValueProvider(NativeCodeGenRequest, PortableGenerator()))
    retort = Retort(recipe=recipe)
    assert retort.dump(1, int | None) == 11
    assert retort.dump(None, int | None) is None


def test_native_plan_cache_is_owned_by_retort(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    recipe = [ValueProvider(NativeCodeGenRequest, generator)]
    data = {"left": [1], "right": [2]}
    for retort in (Retort(recipe=recipe), Retort(recipe=recipe)):
        assert retort.load(data, RepeatedContainers) == RepeatedContainers([1], [2])
    assert generator.calls.count("list") == 2


def test_repeated_optional_models_reuse_dumper_dependencies(monkeypatch):
    forbid_x86_compilation(monkeypatch)
    generator = PortableGenerator()
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])
    item = Example(1, [2])
    data = {"left": {"count": 1, "values": [2]}, "right": None}
    assert retort.dump(RepeatedOptional(item, None)) == data
    assert generator.calls.count("model_dumper") == 2
    assert generator.calls.count("list") == 1


@pytest.mark.skipif(sys.version_info < (3, 11), reason="typing.Self requires Python 3.11")
def test_cached_optional_dumpers_preserve_recursive_placeholder_equality(monkeypatch):
    forbid_x86_compilation(monkeypatch)

    @dataclass
    class RecursiveOptional:
        count: int
        child: typing.Self | None

    @dataclass
    class RepeatedRecursive:
        left: RecursiveOptional
        right: RecursiveOptional

    accumulator = CodeGenAccumulator()
    retort = Retort(recipe=[accumulator])
    value = RepeatedRecursive(RecursiveOptional(1, None), RecursiveOptional(2, None))
    assert retort.dump(value) == {"left": {"count": 1, "child": None}, "right": {"count": 2, "child": None}}
    assert [tp for tp, _ in accumulator.code_pairs] == [RecursiveOptional, RepeatedRecursive]


def test_x86_backend_passes_its_compiler_factory_to_every_emitter():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))
    compiled = []

    def factory(name):
        compiled.append(name)
        return X86Compiler(name)

    generator = X86CodeGenerator(compiler_factory=factory)
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])
    cases = [
        (Example, {"count": 1, "values": [2, 3]}),
        (list[int], [1, 2]),
        (tuple[int, str], [1, "text"]),
        (dict[str, int], {"value": 1}),
        (set[int], [1, 2]),
        (Union[FirstVariant, SecondVariant], {"kind": "first", "value": 1}),
    ]
    python = Retort()
    for tp, data in cases:
        result = retort.load(data, tp)
        assert result == python.load(data, tp)
        assert retort.dump(result, tp) == python.dump(result, tp)
    assert "native_list_loader" in compiled
    assert "native_list_dumper" in compiled
    if sys.version_info >= (3, 13):
        if hasattr(ctypes.pythonapi, "_PyTuple_FromArray"):
            assert "native_tuple_loader" in compiled
        assert "native_dict_loader" in compiled
        assert "native_set_loader" in compiled
        assert "native_tagged_union_loader" in compiled
    assert any(name.startswith("model_loader_") for name in compiled)
    assert any(name.startswith("model_dumper_") for name in compiled)
    assert Retort(codegen_backend=CodeGenBackend.PYTHON).native_codegen is None
