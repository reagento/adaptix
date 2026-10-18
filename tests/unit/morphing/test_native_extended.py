# ruff: noqa: DTZ001

import base64
import collections.abc
import gc
import random
import subprocess
import sys
import weakref
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal, InvalidOperation, localcontext
from inspect import getclosurevars
from typing import Literal
from uuid import UUID

import pytest
from tests_helpers import raises_exc

from adaptix import CodeGenBackend, DebugTrail, Retort, dumper, loader
from adaptix._internal.code_tools import x86_64_compiler
from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix._internal.morphing import iterable_provider


@pytest.fixture(autouse=True)
def native_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


def compare(functions, data):
    try:
        expected = functions[0](data)
    except Exception as error:
        raises_exc(error, lambda: functions[1](data))
    else:
        actual = functions[1](data)
        assert actual == expected
        assert type(actual) is type(expected)


@pytest.mark.parametrize(
    ["tp", "data"], [(list[int] | str, [1000, 2000]), (dict[str, int] | str, {"value": 1000})],
)
def test_container_union_without_dictionary_layout(monkeypatch, debug_trail, tp, data):
    from adaptix._internal.code_tools import native_access

    monkeypatch.setattr(native_access, "supports_dictionary_cache", lambda: False)
    retort = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail)
    function = retort.get_loader(tp)
    assert function(data) == data
    assert function("text") == "text"


@pytest.mark.parametrize("tp", [list[int], list[float], tuple[int, ...], set[int], frozenset[int]])
@pytest.mark.parametrize("input_type", [list, tuple, set, frozenset])
def test_iterable_mapping_alias_changes_after_warming(monkeypatch, tp, input_type):
    functions = [Retort(codegen_backend=backend).get_loader(tp)
                 for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64)]
    data = input_type([1000, 2000])
    for _ in range(20):
        compare(functions, data)

    class MappingMeta(type):
        def __instancecheck__(cls, instance):
            return True

    class Mapping(metaclass=MappingMeta):
        pass

    monkeypatch.setattr(iterable_provider, "CollectionsMapping", Mapping)
    compare(functions, data)


def test_iterable_uses_mapping_alias_after_collections_module_changes(monkeypatch):
    functions = [Retort(codegen_backend=backend).get_loader(list[int])
                 for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64)]
    for _ in range(20):
        compare(functions, [1000, 2000])
    monkeypatch.setattr(collections.abc, "Mapping", list)
    compare(functions, [1000, 2000])


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("inline", [False, True])
def test_union_dumper_retains_input_across_custom_callbacks(monkeypatch, debug_trail, inline):
    if not inline:
        monkeypatch.setattr(x86_64_compiler, "MAX_INLINE_STACK_SIZE", 0)
    outcomes = []

    class Value:
        def __init__(self, label):
            self.label = label

    for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64):
        data = [[Value(1000), Value(2000)], "text"]
        references = [weakref.ref(value) for value in data[0]]
        seen = []

        def convert(value, *, data=data, seen=seen, references=references):
            seen.append(value.label)
            if len(seen) == 1:
                data.pop(0)
                gc.collect()
                assert references[1]() is not None
            return value.label

        retort = Retort(codegen_backend=backend, debug_trail=debug_trail, recipe=[dumper(int, convert)])
        function = retort.get_dumper(list[list[int] | dict[str, int] | str])
        outcomes.append((function(data), seen))
        gc.collect()
        assert all(reference() is None for reference in references)
    assert outcomes == [([[1000, 2000]], [1000, 2000])] * 2


@pytest.mark.parametrize("debug_trail", [DebugTrail.FIRST, DebugTrail.ALL])
@pytest.mark.parametrize("variable", [False, True])
def test_partial_tuple_is_hidden_from_gc_callbacks(debug_trail, variable):
    if not variable and sys.version_info < (3, 13):
        pytest.skip("Fixed-tuple native generation requires CPython 3.13 or newer")

    def convert(value):
        gc.collect()
        for candidate in gc.get_objects():
            if type(candidate) is tuple:
                list(candidate)
        return value

    retort = Retort(codegen_backend=CodeGenBackend.X86_64, debug_trail=debug_trail, recipe=[loader(int, convert)])
    data = {1000, 2000, 3000} if variable else [1000, 2000, 3000]
    function = retort.get_loader(tuple[int, ...] if variable else tuple[int, int, int])
    native = getclosurevars(function).nonlocals["loader_"] if debug_trail == DebugTrail.FIRST else function
    assert isinstance(getattr(native, "__self__", None), NativeCode)
    result = function(data)
    assert result == tuple(data)


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("input_type", [list, tuple])
def test_mixed_scalar_tuple_identity_and_float_conversion(debug_trail, input_type):
    functions = [Retort(codegen_backend=backend, debug_trail=debug_trail).get_loader(tuple[int, str, float])
                 for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64)]
    for value in (1.25, 2000, 2**200, True, "bad", 2**10000):
        compare(functions, input_type([1000, "name", value]))
    data = input_type([int("1000"), bytearray(b"name").decode(), float("1.25")])
    gc.collect()
    references = [sys.getrefcount(value) for value in data]
    for _ in range(100):
        result = functions[1](data)
        assert result is not data
        assert all(left is right for left, right in zip(result, data, strict=True))
        del result
    gc.collect()
    assert [sys.getrefcount(value) for value in data] == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("backend", [CodeGenBackend.PYTHON, CodeGenBackend.X86_64])
def test_mixed_scalar_tuple_runs_custom_float_loader(debug_trail, backend):
    calls = []

    def convert(value):
        calls.append(value)
        return value + 1

    retort = Retort(codegen_backend=backend, debug_trail=debug_trail, recipe=[loader(float, convert)])
    function = retort.get_loader(tuple[int, str, float])
    assert function([1000, "name", 1.25]) == (1000, "name", 2.25)
    assert calls == [1.25]


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_nested_list_restores_outer_loop_after_inner_error(debug_trail):
    outcomes = []
    for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64):
        seen = []

        def convert(value, *, seen=seen):
            seen.append(value)
            if value == "bad":
                raise ValueError("inner failure")
            return value

        function = Retort(
            codegen_backend=backend, debug_trail=debug_trail, recipe=[loader(int, convert)],
        ).get_loader(list[list[list[int]]])
        with pytest.raises(Exception, match=r"inner failure|while loading iterable") as caught:
            function([[[1000]], [["bad"]], [[2000], [3000]]])
        outcomes.append((type(caught.value), seen))
    assert outcomes[0] == outcomes[1]
    assert outcomes[1][1] == ([1000, "bad", 2000, 3000] if debug_trail == DebugTrail.ALL else [1000, "bad"])


def test_factory_constructor_observes_mutable_sentinel_cells():
    @dataclass
    class Model:
        id: int
        items: object = field(default_factory=list)

    functions = [Retort(codegen_backend=backend).get_loader(Model)
                 for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64)]
    for _ in range(30):
        assert functions[1]({"id": 1000, "items": None}) == Model(1000, None)
        assert list(vars(functions[1]({"id": 1000}))) == ["id", "items"]
    cells = dict(zip(Model.__init__.__code__.co_freevars, Model.__init__.__closure__, strict=True))
    sentinel_cell = cells.get("__dataclass_HAS_DEFAULT_FACTORY__") or cells["_HAS_DEFAULT_FACTORY"]
    factory_cell = cells.get("__dataclass_dflt_items__") or cells["_dflt_items"]
    sentinel = sentinel_cell.cell_contents
    for value in (sentinel, None, object()):
        sentinel_cell.cell_contents = value
        factory_cell.cell_contents = lambda: ["factory"]
        for _ in range(10):
            compare(functions, {"id": 1000, "items": value})
            compare(functions, {"id": 1000, "items": "explicit"})
    del sentinel_cell.cell_contents
    compare(functions, {"id": 1000, "items": None})


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("operation", ["loading", "dumping"])
@pytest.mark.parametrize("mutation", ["grow", "shrink", "replace_key", "replace_value", "clear", "resize"])
def test_dictionary_mapper_observes_mutations(debug_trail, operation, mutation):  # noqa: C901
    outcomes, traces = [], []
    for backend in (CodeGenBackend.PYTHON, CodeGenBackend.X86_64):
        data = {"first": 1000, "second": 2000, "third": 3000}
        calls = []

        def convert(value, *, calls=calls, data=data):
            calls.append(value)
            if len(calls) == 1:
                if mutation == "grow":
                    data["fourth"] = 4000
                elif mutation == "shrink":
                    del data["second"]
                elif mutation == "replace_key":
                    del data["second"]
                    data["fourth"] = 4000
                elif mutation == "replace_value":
                    data["third"] = 4000
                elif mutation == "clear":
                    data.clear()
                else:
                    for index in range(100):
                        data[f"extra_{index}"] = index
                    for index in range(100):
                        del data[f"extra_{index}"]
            return value * 2

        retort = Retort(
            codegen_backend=backend, debug_trail=debug_trail,
            recipe=[loader(int, convert), dumper(int, convert)],
        )
        function = retort.get_loader(dict[str, int]) if operation == "loading" else retort.get_dumper(dict[str, int])
        try:
            outcomes.append(function(data))
        except Exception as error:
            outcomes.append((type(error), error.args))
        traces.append(calls)
    assert outcomes[0] == outcomes[1]
    assert traces[0] == traces[1]


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("tp", [dict[str, list[float]], dict[int, list[float]], dict[str, date | None]])
def test_dictionary_mapper_preserves_errors_and_references(debug_trail, tp):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(tp) for retort in (python, native)]
    values = ["2025-01-02", "invalid", None] if tp == dict[str, date | None] else [[1000, 2000], ["bad"], [True]]
    data = dict(zip(("first", "second", "third"), values, strict=True))
    if tp == dict[int, list[float]]:
        data = {1000: values[0], "bad": values[1], 2000: values[2]}
    gc.collect()
    references = [sys.getrefcount(value) for value in values]
    for _ in range(20):
        compare(functions, data)
    gc.collect()
    assert [sys.getrefcount(value) for value in values] == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_uuid_roundtrips_spellings_and_errors(debug_trail):
    rng = random.Random(9162)  # noqa: S311
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    values = [UUID(int=rng.getrandbits(128)) for _ in range(200)]
    values.extend((UUID(int=0), UUID(int=(1 << 128) - 1)))
    text = [str(value) for value in values]
    for tp, data in (
        (UUID, text[0]), (list[UUID], text), (tuple[UUID, ...], text),
        (dict[str, UUID], {str(key): value for key, value in enumerate(text)}),
    ):
        load = [retort.get_loader(tp) for retort in (python, native)]
        compare(load, data)
        loaded = load[1](data)
        compare([retort.get_dumper(tp) for retort in (python, native)], loaded)
    load = [retort.get_loader(UUID) for retort in (python, native)]
    for value in (text[0].upper(), "{" + text[0] + "}", "urn:uuid:" + text[0], values[0].hex, "invalid", "", 1, None):
        compare(load, value)
    loaded = native.get_loader(list[UUID])(text)
    assert [hash(value) for value in loaded] == [hash(value) for value in values]
    assert all(value.is_safe is values[0].is_safe for value in loaded)


@pytest.mark.parametrize("target", [Literal[1000, 2000], Literal[-1000, 2000]])
def test_integer_literal_keeps_equality_and_type_semantics(target):
    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    for tp in (target, list[target], tuple[target, ...], dict[str, target]):
        functions = [retort.get_loader(tp) for retort in (python, native)]
        for value in (1000, 2000, -1000, 1000.0, True, False, 2001, 2**100, "1000", None):
            data = value if tp == target else {"key": value} if tp == dict[str, target] else [value]
            compare(functions, data)


@pytest.mark.parametrize("action", ["init_code", "safe_default", "int_global", "str_code", "hex_code", "missing_int"])
def test_uuid_mutations_are_observed_in_isolated_interpreter(action):
    code = """
import uuid
from adaptix import Retort, CodeGenBackend
text = '12345678-1234-5678-abcd-123456789abc'
native = Retort(codegen_backend=CodeGenBackend.X86_64)
python = Retort()
load, dump = native.get_loader(uuid.UUID), native.get_dumper(uuid.UUID)
value = uuid.UUID(text)
for _ in range(30):
    assert load(text) == value
    assert dump(value) == text
action = ACTION
if action == 'init_code':
    def changed(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None, *, is_safe=None):
        object.__setattr__(self, 'int', 42)
        object.__setattr__(self, 'is_safe', is_safe)
    uuid.UUID.__init__.__code__ = changed.__code__
elif action == 'safe_default':
    uuid.UUID.__init__.__kwdefaults__['is_safe'] = uuid.SafeUUID.safe
elif action == 'int_global':
    uuid.int_ = lambda text, base: int(text, base) + 1
elif action == 'str_code':
    def changed(self):
        return 'changed'
    uuid.UUID.__str__.__code__ = changed.__code__
elif action == 'hex_code':
    def changed(self):
        return '1' * 32
    uuid.UUID.hex.fget.__code__ = changed.__code__
else:
    object.__delattr__(value, 'int')
if action in {'init_code', 'safe_default', 'int_global'}:
    expected, actual = python.load(text, uuid.UUID), load(text)
    assert actual.int == expected.int
    assert actual.is_safe is expected.is_safe
elif action == 'missing_int':
    try:
        dump(value)
    except AttributeError:
        pass
    else:
        raise AssertionError('Missing UUID field was not detected')
else:
    assert dump(value) == python.dump(value, uuid.UUID)
""".replace("ACTION", repr(action))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_sequence_subclass_iterator_mutations(debug_trail):
    class Values(list):
        pass

    data = Values([1000, "text", None])
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(list[int | str | None]) for retort in (python, native)]
    for _ in range(10):
        compare(functions, data)
    calls = []

    def iterate(self):
        calls.append(True)
        return iter([2000, "changed"])

    Values.__iter__ = iterate
    compare(functions, data)
    assert len(calls) == 2
    Values.__iter__ = list.__iter__
    for _ in range(10):
        compare(functions, data)


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_dictionary_subclass_items_mutations_and_instance_shadowing(debug_trail):
    class Values(dict):
        pass

    data = Values(first=1000, second="text", third=None)
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(dict[str, int | str | None]) for retort in (python, native)]
    for _ in range(10):
        compare(functions, data)
    calls = []

    def items(self):
        calls.append(True)
        return [("changed", 2000)]

    Values.items = items
    compare(functions, data)
    assert len(calls) == 2
    Values.items = dict.items
    data.items = lambda: [("instance", 3000)]
    compare(functions, data)
    del data.items
    for _ in range(10):
        compare(functions, data)


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize(
    ["tp", "good", "bad"],
    [
        (tuple[int, str, float], [1000, "name", 1.25], [True, 1, "bad"]),
        (tuple[int | None, float], [None, 1.25], ["bad", 1]),
        (tuple[()], [], [1]),
        (set[int], [1000, 1001, 1000], [True, "bad", 1001]),
        (set[int | None], [None, 1001], [False, "bad", None]),
        (dict[int, str], {1000: "ok", 1001: "next"}, {True: "ok", 1001: 1}),
        (dict[int | None, int | None], {None: None, 1000: 1001}, {False: "bad", 1000: False}),
    ],
)
def test_scalar_tuple_set_and_general_dict_errors_and_ownership(debug_trail, tp, good, bad):
    python = Retort(debug_trail=debug_trail)
    retorts = [python, python.replace(codegen_backend=CodeGenBackend.X86_64)]
    load = [retort.get_loader(tp) for retort in retorts]
    for _ in range(20):
        compare(load, good)
        compare(load, bad)
    loaded = load[0](good)
    dump = [retort.get_dumper(tp) for retort in retorts]
    compare(dump, loaded)
    watched = tuple(good.values()) if isinstance(good, dict) else tuple(good)
    gc.collect()
    references = [sys.getrefcount(value) for value in watched]
    for _ in range(30):
        load[1](good)
        dump[1](loaded)
    gc.collect()
    assert [sys.getrefcount(value) for value in watched] == references


@pytest.mark.parametrize("tp", [date, time, datetime])
@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_iso_ranges_offsets_and_timezone_cache_capacity(tp, debug_trail):
    rng = random.Random(3719)  # noqa: S311
    values = []
    for _ in range(500):
        if tp is date:
            values.append(date(rng.randint(1, 9999), rng.randint(1, 12), rng.randint(1, 28)))
        else:
            zone = timezone(timedelta(minutes=rng.randint(-1439, 1439)))
            clock = {
                "hour": rng.randrange(24), "minute": rng.randrange(60), "second": rng.randrange(60),
                "microsecond": rng.randrange(1000000), "tzinfo": zone if rng.randrange(2) else None,
            }
            values.append(time(**clock) if tp is time else datetime(2024, 2, 29, **clock))
    if tp is date:
        values.extend((date(1, 1, 1), date(9999, 12, 31), date(2000, 2, 29)))
    else:
        for micro in (0, 1, 99, 100, 9999, 10000, 100000, 999999):
            for minutes in (0, 330, -330, 1439, -1439):
                clock = {
                    "hour": 3, "minute": 4, "second": 5, "microsecond": micro,
                    "tzinfo": timezone(timedelta(minutes=minutes)),
                }
                values.append(time(**clock) if tp is time else datetime(9999, 12, 31, **clock))
        for delta in (timedelta(seconds=1), timedelta(microseconds=-1)):
            clock = {"hour": 3, "minute": 4, "tzinfo": timezone(delta), "fold": 1}
            values.append(time(**clock) if tp is time else datetime(2025, 1, 2, **clock))
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    texts = [value.isoformat() for value in values]
    load = [retort.get_loader(list[tp]) for retort in (python, native)]
    dump = [retort.get_dumper(list[tp]) for retort in (python, native)]
    for _ in range(3):
        loaded = load[1](texts)
        assert loaded == load[0](texts)
        assert [hash(value) for value in loaded] == [hash(value) for value in load[0](texts)]
        assert dump[1](values) == texts
        assert dump[1](loaded) == dump[0](load[0](texts))


@pytest.mark.parametrize("tp", [time, datetime])
def test_custom_timezone_callbacks_use_standard_isoformat(tp):
    calls = []

    class Zone(tzinfo):
        def utcoffset(self, value):
            calls.append(value)
            return timedelta(minutes=17)

    zone = Zone()
    value = time(3, 4, tzinfo=zone) if tp is time else datetime(2025, 1, 2, tzinfo=zone)
    python = Retort()
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_dumper(list[tp]) for retort in (python, native)]
    expected = functions[0]([value])
    expected_calls = len(calls)
    calls.clear()
    assert functions[1]([value]) == expected
    assert len(calls) == expected_calls


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_base64_random_payloads_and_invalid_spellings(debug_trail):
    rng = random.Random(2718)  # noqa: S311
    payloads = [rng.randbytes(size) for size in (*range(130), 255, 1024)]
    texts = [base64.b64encode(value).decode("ascii") for value in payloads]
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    assert native.get_loader(list[bytes])(texts) == payloads
    assert native.get_dumper(list[bytes])(payloads) == texts
    functions = [retort.get_loader(list[bytes]) for retort in (python, native)]
    for text in (
        "a",
        "ab",
        "abc",
        "a===",
        "====",
        "=AAA",
        "AA=A",
        "a b=",
        "AA\n=",
        "YWJj=",
        "YWJj==",
        "YQ==",
        "YR==",
        "YQ=",
        "a+b/",
        "🙂",
        "éééé",
        "AA\0=",
        1,
        None,
        b"YQ==",
    ):
        compare(functions, [texts[-1], text, "YQ=="])


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
@pytest.mark.parametrize("trap", [False, True])
def test_decimal_context_and_diagnostics(debug_trail, trap):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(list[Decimal]) for retort in (python, native)]
    with localcontext() as context:
        context.traps[InvalidOperation] = trap
        for text in ("1000.125", "1E+123", "Infinity", "-0", "bad", "", 1, True, None):
            if not trap and type(text) is str and text in {"bad", ""}:
                assert functions[0]([text])[0].is_nan()
                assert functions[1]([text])[0].is_nan()
            else:
                compare(functions, [text])


@dataclass
class Click:
    kind: Literal["click"]
    x: int


@dataclass
class Text:
    kind: Literal["text"]
    text: str


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_tagged_union_errors_mutations_and_subclasses(debug_trail):
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(list[Click | Text]) for retort in (python, native)]
    good = [{"kind": "click", "x": 1000}, {"kind": "text", "text": "message"}]
    for _ in range(20):
        compare(functions, good)
    for row in (
        {"kind": "click", "x": "bad"},
        {"kind": "text", "text": 1},
        {"kind": "click"},
        {"kind": "other", "x": 1},
        {"x": 1},
        {"kind": None},
        {1: "bad", "kind": "click"},
    ):
        compare(functions, [good[0], row])

    class Child(Click):
        pass

    dump = [retort.get_dumper(list[Click | Text]) for retort in (python, native)]
    compare(dump, [Child("click", 1), Text("text", "message")])


def test_factory_defaults_preserve_calls_and_exceptions():
    calls = []

    def factory():
        calls.append(1)
        if len(calls) == 2:
            raise ValueError("factory failed")
        return [1000]

    @dataclass
    class Model:
        id: int
        values: list[int] = field(default_factory=factory)

    python = Retort()
    retorts = [python, python.replace(codegen_backend=CodeGenBackend.X86_64)]
    errors = []
    for retort in retorts:
        calls.clear()
        function = retort.get_loader(Model)
        assert function({"id": 1}).values == [1000]
        with pytest.raises(Exception, match=r".+") as caught:
            function({"id": 2})
        errors.append(caught.value)
        assert calls == [1, 1]
    raises_exc(errors[0], lambda: (_ for _ in ()).throw(errors[1]))


@pytest.mark.parametrize("tp", ["tuple[int, str]", "set[int]"])
def test_mapping_registration_after_warming_fixed_containers(tp):
    code = f"""
from collections.abc import Mapping
from adaptix import Retort, CodeGenBackend
from adaptix.load_error import ExcludedTypeLoadError
function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader({tp})
values = [1000, "name"] if {tp!r}.startswith("tuple") else [1000]
for _ in range(20):
    function(values)
Mapping.register(list)
try:
    function(values)
except ExcludedTypeLoadError:
    pass
else:
    raise AssertionError("Mapping exclusion was bypassed")
"""
    process = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)  # noqa: S603
    assert process.returncode == 0, process.stdout + process.stderr


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_selected_union_constructor_failure_runs_once(debug_trail):
    seen = []

    @dataclass
    class Failing:
        kind: Literal["fail"]
        value: int

        def __post_init__(self):
            seen.append(self.value)
            raise ValueError("constructor failed")

    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(list[Failing | Text]) for retort in (python, native)]
    data = [{"kind": "fail", "value": 1000}]
    with pytest.raises(Exception, match=r".+") as caught:
        functions[0](data)
    assert seen == [1000]
    seen.clear()
    raises_exc(caught.value, lambda: functions[1](data))
    assert seen == [1000]


def test_warm_timezone_cache_does_not_retain_loaded_objects():
    function = Retort(codegen_backend=CodeGenBackend.X86_64).get_loader(list[datetime])
    texts = ["2025-01-02T03:04:05.123456+05:30", "2025-01-02T03:04:05-03:45"]
    for _ in range(10):
        function(texts)
    gc.collect()
    values = function(texts)
    zones = [value.tzinfo for value in values]
    references = [sys.getrefcount(zone) for zone in zones]
    for _ in range(100):
        actual = function(texts)
        assert actual == values
        del actual
    gc.collect()
    assert [sys.getrefcount(zone) for zone in zones] == references


@pytest.mark.parametrize("debug_trail", list(DebugTrail))
def test_sparse_invalid_dictionary_keys_do_not_call_equality(debug_trail):
    seen = []

    class Key:
        def __hash__(self):
            return 0

        def __eq__(self, other):
            seen.append(1)
            return self is other

    keys = [Key() for _ in range(80)]
    data = {key: 1000 for key in keys}
    for key in keys[:70]:
        del data[key]
    python = Retort(debug_trail=debug_trail)
    native = python.replace(codegen_backend=CodeGenBackend.X86_64)
    functions = [retort.get_loader(dict[int, int]) for retort in (python, native)]
    errors = []
    for function in functions:
        seen.clear()
        with pytest.raises(Exception, match=r".+") as caught:
            function(data)
        errors.append(caught.value)
        assert seen == []
    raises_exc(errors[0], lambda: (_ for _ in ()).throw(errors[1]))
