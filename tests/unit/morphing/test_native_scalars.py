# ruff: noqa: DTZ001

import ctypes
import gc
import random
import subprocess
import sys
import weakref
from dataclasses import dataclass, make_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import pytest
from tests_helpers import raises_exc, reference_counts

from adaptix import CodeGenBackend, DebugTrail, Retort, name_mapping
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler, check_native_platform
from adaptix._internal.morphing.model.native_runtime import MISSING


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize(["tp", "data"], [
    (list[int], [1000, True, "bad", 1001]),
    (list[float], [1.25, 3, "bad", 2.5]),
    (list[int | None], [1000, None, "bad", False]),
    (dict[str, int], {"good": 1000, "bad": True, 3: "bad"}),
    (dict[str, int | None], {"good": 1000, "none": None, "bad": "bad"}),
])
def test_scalar_container_failures_keep_python_trails_and_references(debug_trail, tp, data):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(tp) for retort in (python, native)]
    watched = [
        value for value in (data.values() if isinstance(data, dict) else data)
        if type(value) is float or (type(value) is int and value > 256)
    ]
    references = reference_counts(watched)
    with pytest.raises(Exception, match=r".+") as expected:
        functions[0](data)
    for _ in range(30):
        raises_exc(expected.value, lambda: functions[1](data))
    del expected
    assert reference_counts(watched) == references


def test_scalar_copy_handles_sparse_and_split_dictionaries():
    class Carrier:
        pass

    source = Carrier()
    source.first, source.second = 1000, 1001
    retort = Retort(codegen_backend=CodeGenBackend.X86_64)
    load, dump = retort.get_loader(dict[str, int]), retort.get_dumper(dict[str, int])
    values = {f"key_{index}": 1000 + index for index in range(80)}
    for index in range(0, 80, 2):
        del values[f"key_{index}"]
    for data in (values, vars(source), {}, {"a": 1000}):
        for function in (load, dump):
            result = function(data)
            assert result == data
            assert result is not data
            assert all(key is original for key, original in zip(result, data, strict=True))


@pytest.mark.parametrize("mutation", ["grow", "shrink", "replace"])
@pytest.mark.parametrize(["tp", "initial", "replacement"], [
    (list[int], [1000, 1001], [3000, 3001]),
    (list[int | str], [1000, "first"], ["second", 3001]),
    (list[int | str | None], [1000, "first", None], [None, "second"]),
])
def test_allocation_callbacks_change_reserved_scalar_list_input(monkeypatch, mutation, tp, initial, replacement):
    original_address = ctypes.cast(ctypes.pythonapi.PyList_New, ctypes.c_void_p).value
    original = ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.c_ssize_t)(original_address)
    data = list(initial)
    armed = []

    def allocate(size):
        pointer = original(size)
        if armed:
            armed.clear()
            if mutation == "grow":
                data.extend(range(2000, 2100))
            elif mutation == "shrink":
                data.clear()
            else:
                data[:] = replacement
            gc.collect()
        return pointer

    callback = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_ssize_t)(allocate)
    monkeypatch.setattr(ctypes.pythonapi, "PyList_New", callback)
    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(tp)
    for _ in range(30):
        assert function(list(initial)) == initial
    armed.append(True)
    actual = function(data)
    assert not armed
    assert actual == data


@pytest.mark.parametrize("action", ["register", "replace_mapping", "replace_instancecheck", "clear_cache"])
def test_mapping_guard_changes_are_observed_in_isolated_interpreter(action):
    code = """
import _abc as abc_accelerator
import collections.abc
from adaptix import CodeGenBackend, Retort
from adaptix._internal.morphing import iterable_provider
from adaptix.load_error import ExcludedTypeLoadError
function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(list[int])
for _ in range(30):
    assert function([1000]) == [1000]
action = ACTION
if action == "register":
    collections.abc.Mapping.register(list)
elif action == "replace_mapping":
    iterable_provider.CollectionsMapping = list
elif action == "replace_instancecheck":
    type(collections.abc.Mapping).__instancecheck__ = lambda cls, value: True
else:
    abc_accelerator._reset_caches(collections.abc.Mapping)
    assert function([1000]) == [1000]
    collections.abc.Mapping.register(list)
try:
    function([1000])
except Exception as error:
    from adaptix.load_error import AggregateLoadError
    assert isinstance(error, (ExcludedTypeLoadError, AggregateLoadError)), type(error)
else:
    raise AssertionError("Mapping exclusion was skipped")
""".replace("ACTION", repr(action))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_iso_datetime_range_fractions_and_fallbacks(debug_trail):
    randomizer = random.Random(9127)  # noqa: S311
    values = [datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59, 999999), datetime(2000, 2, 29)]
    for _ in range(500):
        year = randomizer.randint(1, 9999)
        value = datetime(year, randomizer.randint(1, 12), 1)
        values.append(value + timedelta(
            days=randomizer.randrange(28), seconds=randomizer.randrange(86400),
            microseconds=randomizer.randrange(1000000),
        ))
    values.extend(datetime(2024, 2, 29, 3, 4, 5, microsecond) for microsecond in (0, 1, 99, 100, 9999, 10000, 100000))
    values.extend((
        datetime(2024, 2, 29, tzinfo=timezone.utc),
        datetime(2024, 2, 29, tzinfo=timezone(timedelta(hours=-3, minutes=-30))),
        datetime(2024, 2, 29, fold=1),
    ))
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    dump = native.get_dumper(list[datetime])
    text = [value.isoformat() for value in values]
    assert dump(values) == text
    loaded = native.get_loader(list[datetime])(text)
    assert loaded == python.get_loader(list[datetime])(text)
    assert dump(loaded) == text
    assert [hash(value) for value in loaded] == [hash(value) for value in values]
    assert sorted(loaded[:500]) == sorted(values[:500])
    assert all(value.fold == 0 for value in loaded)


@pytest.mark.parametrize("text", [
    "1900-02-29T03:04:05", "0000-01-01T00:00:00", "2024-02-30T01:02:03",
    "2024-13-01T00:00:00", "2024-01-00T00:00:00", "2024-01-01T24:00:00",
    "2024-01-01T00:60:00", "2024-01-01T00:00:60", "2024-01-01T00:00:00.12a456",
    "2024-01-01T00:00:00.00000/", "2024-01-01T00:00:00.99999:",
    "2024-01-01T00:00:00.éééééé", "2024-01-01", "20240101T000000", "2024-W01-1T00:00:00",
    "2024-01-01 00:00:00", "2024-01-01T00:00:00.123", "2024-01-01T00:00:00Z",
])
def test_iso_datetime_noncanonical_and_invalid_inputs(text):
    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(list[datetime]) for retort in (python, native)]
    data = ["2024-01-01T00:00:00", text]
    try:
        expected = functions[0](data)
    except Exception as error:
        raises_exc(error, lambda: functions[1](data))
    else:
        assert functions[1](data) == expected


def test_enum_hash_mutation_after_warming_keeps_dictionary_semantics():
    class State(str, Enum):
        OPEN = "open"
        CLOSED = "closed"

    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_dumper(list[State]) for retort in (python, native)]
    data = [State.OPEN, State.CLOSED]
    for _ in range(30):
        assert functions[1](data) == functions[0](data)

    def broken_hash(value):
        raise ValueError("hash changed")

    State.__hash__ = broken_hash
    with pytest.raises(Exception, match=r".+") as expected:
        functions[0](data)
    raises_exc(expected.value, lambda: functions[1](data))


def test_plain_enum_renaming_preserves_hash_lookup():
    class State(Enum):
        OPEN = "open"
        CLOSED = "closed"

    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_dumper(list[State]) for retort in (python, native)]
    data = [State.OPEN, State.CLOSED]
    for _ in range(30):
        assert functions[1](data) == functions[0](data)
    State.OPEN._name_ = "RENAMED"
    try:
        expected = functions[0](data)
    except Exception as error:
        raises_exc(error, lambda: functions[1](data))
    else:
        # A changed hash may still reach the same bucket and identity match.
        assert functions[1](data) == expected


def test_enum_member_class_changes_keep_lookup_semantics():
    class State(str, Enum):
        OPEN = "open"

    class Changed(str):  # noqa: SLOT000  # Match the enum member's dictionary layout.
        def __hash__(self):
            raise ValueError("changed member class")

    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_dumper(list[State]) for retort in (python, native)]
    data = [State.OPEN]
    for _ in range(30):
        assert functions[1](data) == ["open"]
    State.OPEN.__class__ = Changed
    with pytest.raises(Exception, match=r".+") as expected:
        functions[0](data)
    raises_exc(expected.value, lambda: functions[1](data))


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_fused_default_filters_release_every_row_reference(debug_trail):
    @dataclass
    class Model:
        value: str = "default"

    python = Retort(recipe=[name_mapping(omit_default=True)], debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_dumper(list[Model]) for retort in (python, native)]
    values = [bytearray(f"value_{index}".encode()).decode() for index in range(10)]
    data = [Model(value) for value in values] + [Model()]
    for _ in range(30):
        assert functions[1](data) == functions[0](data)
    gc.collect()
    counts = [sys.getrefcount(value) for value in values]
    for _ in range(30):
        assert functions[1](data) == functions[0](data)
    gc.collect()
    assert [sys.getrefcount(value) for value in values] == counts


@pytest.mark.parametrize(["attribute", "value"], [("platform", "win32"), ("maxsize", 2**31 - 1)])
def test_python_enum_provider_does_not_inspect_unsupported_object_layouts(monkeypatch, attribute, value):
    if sys.version_info[:2] not in {(3, 13), (3, 14), (3, 15)}:
        pytest.skip("Private enum storage is enabled on 3.13-3.15")
    from adaptix._internal.code_tools import native_access

    class State(str, Enum):
        OPEN = "open"

    def forbidden(*args):
        pytest.fail("Python backend inspected a private object layout")

    monkeypatch.setattr(native_access, "LOOKUP", forbidden)
    monkeypatch.setattr(sys, attribute, value)
    retort = Retort()
    assert retort.load("open", State) is State.OPEN
    assert retort.dump(State.OPEN, State) == "open"


@pytest.mark.parametrize("count", [4, 32])
def test_model_storage_and_default_mutations_after_warming(count):
    model = make_dataclass("Model", [(f"field_{index}", Any) for index in range(count - 1)] + [("last", Any, None)])
    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    load = native.get_loader(model)
    dump = native.get_dumper(model)
    values = [object() for _ in range(count - 1)]
    data = {f"field_{index}": value for index, value in enumerate(values)}
    for _ in range(30):
        value = load(data)
        assert dump(value) == python.dump(value, model)
    model.__init__.__defaults__ = ("changed",)
    assert dump(load(data)) == python.dump(python.load(data, model), model)
    assert load(data).last is None  # Defaults fixed by the loading shape.
    value = load(data)
    value.__dict__ = {**vars(value), "field_0": "replacement"}
    assert dump(value) == python.dump(value, model)
    del value.field_0
    with pytest.raises(Exception, match=r".+") as expected:
        python.dump(value, model)
    raises_exc(expected.value, lambda: dump(value))


def test_omitted_native_constructor_reads_current_defaults():
    @dataclass
    class Model:
        first: Any
        last: Any = None

    compiler = X86Compiler("omitted_constructor")
    args = tuple(compiler.dict_lookup(compiler.data, name, MISSING) for name in ("first", "last"))
    result = compiler.construct_object(Model, args, (), ("first", "last"), steal=True, omitted=MISSING)
    function = compiler.finish(result).make_callable()
    for _ in range(30):
        assert function({"first": 1000}) == Model(1000)
    Model.__init__.__defaults__ = ("changed",)
    assert function({"first": 1000}) == Model(1000)
    assert function({"first": 1000, "last": None}) == Model(1000, None)
    Model.__init__.__defaults__ = None
    with pytest.raises(TypeError):
        function({"first": 1000})


def test_converter_program_metadata_does_not_retain_recursive_graphs():
    from adaptix._internal.morphing.native.descriptions import OptionalProgram
    from adaptix._internal.morphing.native.registry import get_program, register_program

    def factory():
        def converter(value):
            return value
        program = OptionalProgram(converter, converter)
        register_program(converter, program)
        assert get_program(converter) is not None
        return weakref.ref(converter)

    reference = factory()
    gc.collect()
    assert reference() is None
