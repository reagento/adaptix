import gc
import sys
from dataclasses import dataclass
from typing import List

import pytest
from tests_helpers import raises_exc, reference_counts

from adaptix import CodeGenBackend, DebugTrail, Retort, dumper, loader
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix.load_error import LoadError


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("loading", [False, True])
@pytest.mark.parametrize("mutation", ["append", "delete", "replace", "clear"])
def test_callbacks_observe_list_iterator_mutation_rules(debug_trail, loading, mutation):
    def run(backend):
        data = ["first", "second", "third"]
        seen = []

        def convert(value):
            seen.append(value)
            if value == "first":
                if mutation == "append":
                    data.extend(["fourth", "fifth"])
                elif mutation == "delete":
                    data.pop(0)
                elif mutation == "replace":
                    data[1] = "changed"
                else:
                    data.clear()
            return value

        retort = Retort(
            codegen_backend=backend, debug_trail=debug_trail,
            recipe=[loader(str, convert) if loading else dumper(str, convert)],
        )
        function = retort.get_loader(List[str]) if loading else retort.get_dumper(List[str])
        return function(data), seen

    assert run(CodeGenBackend.X86_64) == run(CodeGenBackend.PYTHON)


@dataclass
class Model:
    first: int
    second: str


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("loading", [False, True])
def test_fused_model_errors_and_reference_cleanup(debug_trail, loading):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    if loading:
        functions = [retort.get_loader(List[Model]) for retort in (python, native)]
        good = [{"first": 1, "second": "ok"}]
        bad = [{"first": "bad", "second": 2}, {}, {"first": 3, "second": "ok"}]
    else:
        functions = [retort.get_dumper(List[Model]) for retort in (python, native)]
        good = [Model(1, "ok")]
        broken = Model(2, "bad")
        del broken.first
        del broken.second
        bad = [good[0], broken, good[0]]
    for _ in range(20):
        assert functions[1](good) == functions[0](good)
    references = reference_counts(bad)
    with pytest.raises(Exception, match=r".+") as reference:
        functions[0](bad)
    for _ in range(20):
        raises_exc(reference.value, lambda: functions[1](bad))
        assert functions[1](good) == functions[0](good)
    del reference
    assert reference_counts(bad) == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_fused_constructor_base_exception_does_not_leak_arguments(debug_trail):
    class Broken:
        def __init__(self, value: object):
            raise KeyboardInterrupt

    retort = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail)
    function = retort.get_loader(List[Broken])
    value = object()
    data = [{"value": value}]
    references = reference_counts([value])
    for _ in range(20):
        with pytest.raises(KeyboardInterrupt):
            function(data)
    assert reference_counts([value]) == references


def test_reserved_list_never_exposes_uninitialized_elements_to_gc():
    data = [str(index) for index in range(5)]

    def convert(value):
        gc.collect()
        # Iterating a list with a published NULL slot would crash CPython.
        for obj in gc.get_objects():
            if type(obj) is list:
                tuple(obj)
        return value

    retort = Retort(codegen_backend=CodeGenBackend.X86_64, recipe=[loader(str, convert)])
    assert retort.load(data, List[str]) == data


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize(["tp", "data"], [
    (list[int | str], [int("1000"), b"scalar union".decode()]),
    (list[int | str | None], [1000, "value", None]),
    (list[int | str | bool], [1000, "value", True, False]),
    (list[int | str | bool | float | None], [1000, "value", True, 1.25, None]),
    (list[float | int], [1000, 1.25]),
    (list[int | float], [1000, 1.25]),
])
def test_scalar_union_lists_preserve_types_identity_and_references(debug_trail, tp, data):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(tp) for retort in (python, native)]
    watched = [value for value in data if value is not None and type(value) is not bool]
    gc.collect()
    references = [sys.getrefcount(value) for value in watched]
    for source in ([], data, tuple(data)):
        reference = functions[0](source)
        for _ in range(30):
            actual = functions[1](source)
            assert actual == reference
            assert [type(value) for value in actual] == [type(value) for value in reference]
            assert all(
                wanted is not original or converted is original
                for original, converted, wanted in zip(source, actual, reference, strict=True)
            )
            del actual
        del reference
    del source
    gc.collect()
    assert [sys.getrefcount(value) for value in watched] == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("bad_index", [0, 1, 2])
@pytest.mark.parametrize("nullable", [False, True])
def test_scalar_union_list_failure_after_partial_copy(debug_trail, bad_index, nullable):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    tp = list[int | str | None] if nullable else list[int | str]
    data = [int("1000"), b"scalar union".decode(), int("1001")]
    data[bad_index] = object()
    functions = [retort.get_loader(tp) for retort in (python, native)]
    references = reference_counts(data)
    with pytest.raises(LoadError) as expected:
        functions[0](data)
    for _ in range(30):
        raises_exc(expected.value, lambda: functions[1](data))
    del expected
    assert reference_counts(data) == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_scalar_union_list_keeps_custom_converter_calls_and_mutations(debug_trail):
    def run(backend):
        source = ["first", 1000, "last"]
        seen = []

        def convert(value):
            seen.append(value)
            if value == "first":
                source.append("appended")
            return str(value).upper()

        retort = Retort(codegen_backend=backend, debug_trail=debug_trail, recipe=[loader(str, convert)])
        return retort.load(source, list[int | str]), seen

    assert run(CodeGenBackend.X86_64) == run(CodeGenBackend.PYTHON)
