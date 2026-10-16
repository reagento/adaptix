import gc
import inspect
import sys
import weakref
from collections import UserDict
from collections.abc import Mapping
from dataclasses import dataclass
from types import FunctionType
from typing import Annotated

import pytest

from adaptix import DebugTrail, Retort, loader
from adaptix._internal.code_tools.cpython_layout.selection import require_cpython_layout
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform
from adaptix._internal.morphing.native.codegen import NativeCodeGenRequest
from adaptix._internal.morphing.native.xdsl.compiler import LLVMCode
from adaptix._internal.morphing.native.xdsl.generator import XDSLCodeGenerator
from adaptix._internal.provider.value_provider import ValueProvider
from adaptix.load_error import AggregateLoadError


@dataclass(slots=True)
class Model:
    value: int
    text: str
    flag: bool


@dataclass
class OptionalModel:
    value: int = 1


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
        require_cpython_layout()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def retort(opt_level=2, debug_trail=DebugTrail.ALL, recipe=()):
    generator = XDSLCodeGenerator(opt_level=opt_level)
    return Retort(debug_trail=debug_trail, recipe=[ValueProvider(NativeCodeGenRequest, generator), *recipe]), generator


@pytest.mark.parametrize("opt_level", [0, 2, 3])
@pytest.mark.parametrize(
    ["tp", "data"],
    [
        (int, 300),
        (str, "test"),
        (list[int], [1, 2, 300]),
        (list[int | str | None], [1, "two", None]),
        (Model, {"value": 300, "text": "test", "flag": True}),
    ],
)
def test_load_dump_and_public_signature(opt_level, tp, data):
    r, gen = retort(opt_level)
    python = Retort()
    load, dump = r.get_loader(tp), r.get_dumper(tp)
    result = load(data)
    assert result == python.load(data, tp)
    assert dump(result) == python.dump(result, tp)
    assert isinstance(load.__self__, LLVMCode)
    assert str(inspect.signature(load)) == "(data)"
    assert load(data=data) == result
    for args, kwargs in [((), {}), ((data, data), {}), ((data,), {"data": data}), ((), {"other": data})]:
        with pytest.raises(TypeError):
            load(*args, **kwargs)
    assert gen.codes


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize(
    ["tp", "data"],
    [
        (int, True),
        (list[int], [1, "bad", 3]),
        (Model, {"value": "bad", "text": 4}),
        (Model, UserDict(value=1, text="test", flag=True)),
    ],
)
def test_fallback_and_errors_match_python(debug_trail, tp, data):
    r = retort(debug_trail=debug_trail)[0]
    python = Retort(debug_trail=debug_trail)
    try:
        expected = python.load(data, tp)
    except Exception as error:
        with pytest.raises(type(error)) as captured:
            r.load(data, tp)
        assert str(captured.value) == str(error)  # noqa: PT017
    else:
        assert r.load(data, tp) == expected


def test_reference_counts_and_cross_backend_calls():
    r = retort()[0]
    load = r.get_loader(list[str])
    value = "unique " + str(object())
    data = [value, value]
    count = sys.getrefcount(value)
    for sample in [data] * 20:
        result = load(sample)
        assert result == data
        assert result is not data
        del result
    assert sys.getrefcount(value) == count
    scalar = r.get_loader(str)
    compiler = X86Compiler("call_xdsl")
    result = compiler.call(scalar, compiler.data)
    caller = compiler.finish(result).make_callable()
    assert caller(value) is value
    assert sys.getrefcount(value) == count


def test_constructor_mutation_and_error_release_references():
    events = []

    class ModelWithConstructor:
        def __init__(self, value: str):
            events.append(value)
            data.clear()
            raise ValueError("constructor failed")

    r = retort()[0]
    value = "unique " + str(object())
    data = {"value": value}
    count = sys.getrefcount(value)
    load = r.get_loader(ModelWithConstructor)
    assert isinstance(load.__self__, LLVMCode)
    with pytest.raises(ValueError, match="constructor failed"):
        load(data)
    events.clear()
    assert sys.getrefcount(value) == count - 1


def test_unsupported_models_preserve_custom_converters():
    r, gen = retort(recipe=[loader(int, lambda value: value + 10)])
    assert r.load({"value": 1}, OptionalModel) == OptionalModel(11)
    assert r.load({}, OptionalModel) == OptionalModel(1)
    assert gen.fallbacks


def test_escaped_loader_keeps_jit_alive_and_cycles_are_collectable():
    r, gen = retort()
    load = r.get_loader(Model)
    reference = weakref.ref(gen)
    del r, gen
    gc.collect()
    assert load({"value": 1, "text": "test", "flag": True}) == Model(1, "test", flag=True)
    assert reference() is None
    del load
    gc.collect()


def test_dumper_class_mutation_invalidates_slot_guard():
    r = retort()[0]
    dump = r.get_dumper(Model)
    original = Model.text
    value = Model(1, "original", flag=True)
    try:
        Model.text = property(lambda self: "changed")
        assert dump(value)["text"] == "changed"
    finally:
        Model.text = original


def test_nested_model_and_annotations_fallback():
    @dataclass
    class Nested:
        child: Annotated[Model, "metadata"]

    r, gen = retort()
    data = {"child": {"value": 1, "text": "test", "flag": True}}
    value = r.load(data, Nested)
    assert value == Nested(Model(1, "test", flag=True))
    assert r.dump(value, Nested) == data
    assert gen.fallbacks


def test_partial_list_type_failure_releases_owned_items():
    r = retort()[0]
    load = r.get_loader(list[str])
    value = "unique " + str(object())
    data = [value, value, 123]
    count = sys.getrefcount(value)
    with pytest.raises(AggregateLoadError):
        load(data)
    gc.collect()
    assert sys.getrefcount(value) == count


def test_abc_registration_invalidates_list_guard():
    r = retort()[0]
    load = r.get_loader(list[int])
    fallback = next(value for value in load.__self__.constants if type(value) is FunctionType)
    events = []

    def profile(frame, event, arg):
        if event == "call" and frame.f_code is fallback.__code__:
            events.append(event)

    class VirtualMapping:
        pass

    previous = sys.getprofile()
    try:
        sys.setprofile(profile)
        assert load([1, 2]) == [1, 2]
        assert not events
        Mapping.register(VirtualMapping)
        assert load([1, 2]) == [1, 2]
        assert events
    finally:
        sys.setprofile(previous)
