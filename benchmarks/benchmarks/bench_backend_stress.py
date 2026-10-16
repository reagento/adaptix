# ruff: noqa: S101
import base64
import json
import subprocess
import sys
from dataclasses import dataclass, field, make_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

import msgspec
import pytest

from adaptix import CodeGenBackend, DebugTrail, Retort, name_mapping
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix.load_error import LoadError
from benchmarks import bench_backend_matrix as matrix
from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures import bench_adaptix, bench_msgspec
from benchmarks.simple_structures.common import create_book, create_dumped_book

IMPLEMENTATIONS = ("adaptix_x86_64", "msgspec")
FIELDS = [("id", int), ("name", str), ("score", float), ("active", bool)]
FlatDataclass = make_dataclass("FlatDataclass", FIELDS, namespace={"__module__": __name__})
SlotDataclass = make_dataclass("SlotDataclass", FIELDS, slots=True, namespace={"__module__": __name__})
FrozenDataclass = make_dataclass("FrozenDataclass", FIELDS, frozen=True, namespace={"__module__": __name__})
FlatStruct = msgspec.defstruct("FlatStruct", FIELDS, module=__name__)
FrozenStruct = msgspec.defstruct("FrozenStruct", FIELDS, frozen=True, module=__name__)
WIDE_FIELDS = [(f"field_{index}", int) for index in range(128)]
WideDataclass = make_dataclass("WideDataclass", WIDE_FIELDS, namespace={"__module__": __name__})
WideStruct = msgspec.defstruct("WideStruct", WIDE_FIELDS, module=__name__)


@dataclass
class FactoryDataclass:
    id: int
    items: list[int] = field(default_factory=list)


class FactoryStruct(msgspec.Struct):
    id: int
    items: list[int] = msgspec.field(default_factory=list)


@dataclass
class PostInitDataclass:
    id: int
    name: str

    def __post_init__(self):
        self.name = self.name.strip()


class PostInitStruct(msgspec.Struct):
    id: int
    name: str

    def __post_init__(self):
        self.name = self.name.strip()


@dataclass
class TreeDataclass:
    value: int
    children: "list[TreeDataclass]"


class TreeStruct(msgspec.Struct):
    value: int
    children: "list[TreeStruct]"


@dataclass
class ClickDataclass:
    kind: Literal["click"]
    x: int
    y: int


@dataclass
class TextDataclass:
    kind: Literal["text"]
    text: str


class ClickStruct(msgspec.Struct, tag="click", tag_field="kind"):
    x: int
    y: int


class TextStruct(msgspec.Struct, tag="text", tag_field="kind"):
    text: str


WORKLOADS = (
    *(f"list_int_{size}" for size in (0, 1, 10, 100, 10000, 100000)),
    *(f"dict_str_int_{size}" for size in (0, 1, 10, 100, 10000)),
    "list_str_unicode_1000", "list_float_1000", "list_bool_1000",
    "list_union_int_str_1000", "list_union_optional_int_str_1000", "list_tuple_1000", "set_int_1000",
    "dict_int_str_1000", "dict_unicode_int_1000", "list_date_100", "list_time_100",
    "list_datetime_aware_100", "list_bytes_1000", "list_uuid_1000", "list_decimal_1000",
    "slotted_model", "frozen_model", "post_init_model", "default_factory_model",
    "recursive_tree_20", "tagged_union_1000", "list_models_1000", "wide_model_128",
    "book_fresh_keys_100", "book_1000",
)
ERROR_WORKLOADS = ("list_bad_first", "list_bad_last", "list_bad_all", "model_bad_field", "model_missing_field")
JSON_WORKLOADS = ("flat_model", "book_100")


def create_retort(debug_trail=DebugTrail.ALL, *, codegen_backend=CodeGenBackend.X86_64):
    return Retort(codegen_backend=codegen_backend, strict_coercion=True, debug_trail=debug_trail)


def tree(cls, depth):
    if not depth:
        return cls(value=1000, children=[]), {"value": 1000, "children": []}
    child, data = tree(cls, depth - 1)
    return cls(value=1000 + depth, children=[child]), {"value": 1000 + depth, "children": [data]}


def create_case(workload, implementation):  # noqa: C901, PLR0911, PLR0912, PLR0915
    native = implementation == "adaptix_x86_64"
    retort = create_retort(codegen_backend=CodeGenBackend.X86_64 if native else CodeGenBackend.PYTHON)

    def simple(target, data, loaded=None, dumped=None):
        return matrix.Case(target, data, data if loaded is None else loaded, data if dumped is None else dumped, retort)

    if workload.startswith("list_int_"):
        return simple(list[int], list(range(1000, 1000 + int(workload.rsplit("_", 1)[1]))))
    if workload.startswith("dict_str_int_"):
        return simple(dict[str, int], {f"key_{i}": 1000 + i for i in range(int(workload.rsplit("_", 1)[1]))})
    if workload == "list_str_unicode_1000":
        return simple(list[str], [f"строка_日本語_🙂_{i}" for i in range(1000)])
    if workload == "list_float_1000":
        return simple(list[float], [1000 + i / 10 for i in range(1000)])
    if workload == "list_bool_1000":
        return simple(list[bool], [bool(i % 2) for i in range(1000)])
    if workload == "list_union_int_str_1000":
        return simple(list[int | str], [1000 + i if i % 2 else f"name_{i}" for i in range(1000)])
    if workload == "list_union_optional_int_str_1000":
        return simple(list[int | str | None], [None if i % 3 == 0 else
                      1000 + i if i % 3 == 1 else f"name_{i}" for i in range(1000)])
    if workload == "list_tuple_1000":
        data = [[1000 + i, f"name_{i}", i / 10] for i in range(1000)]
        loaded = [tuple(row) for row in data]
        return simple(list[tuple[int, str, float]], data, loaded, loaded)
    if workload == "set_int_1000":
        data = list(range(1000, 2000))
        loaded = set(data)
        return simple(set[int], data, loaded, list(loaded))
    if workload == "dict_int_str_1000":
        return simple(dict[int, str], {1000 + i: f"name_{i}" for i in range(1000)})
    if workload == "dict_unicode_int_1000":
        return simple(dict[str, int], {f"ключ_日本語_🙂_{i}": 1000 + i for i in range(1000)})
    if workload == "list_date_100":
        loaded = [date(2025, 1, 1) + timedelta(days=i) for i in range(100)]
        return simple(list[date], [value.isoformat() for value in loaded], loaded)
    if workload == "list_time_100":
        loaded = [time(3, 4, 5, 1000 + i) for i in range(100)]
        return simple(list[time], [value.isoformat() for value in loaded], loaded)
    if workload == "list_datetime_aware_100":
        tz = timezone(timedelta(hours=5, minutes=30))
        loaded = [datetime(2025, 1, 2, 3, 4, 5, 1000 + i, tzinfo=tz) for i in range(100)]
        return simple(list[datetime], [value.isoformat() for value in loaded], loaded)
    if workload == "list_bytes_1000":
        loaded = [f"payload_{i}".encode() + b"\x00\xff" for i in range(1000)]
        return simple(list[bytes], [base64.b64encode(value).decode() for value in loaded], loaded)
    if workload == "list_uuid_1000":
        loaded = [UUID(int=1000 + i) for i in range(1000)]
        return simple(list[UUID], [str(value) for value in loaded], loaded)
    if workload == "list_decimal_1000":
        data = [f"{1000 + i}.125" for i in range(1000)]
        return simple(list[Decimal], data, [Decimal(value) for value in data])
    if workload in {"slotted_model", "frozen_model", "list_models_1000"}:
        if native:
            cls = {
                "slotted_model": SlotDataclass,
                "frozen_model": FrozenDataclass,
                "list_models_1000": FlatDataclass,
            }[workload]
        else:
            cls = FrozenStruct if workload == "frozen_model" else FlatStruct
        data = {"id": 12345, "name": "example", "score": 1.25, "active": True}
        if workload == "list_models_1000":
            rows = [{**data, "id": 1000 + i, "name": f"name_{i}"} for i in range(1000)]
            return simple(list[cls], rows, [cls(**row) for row in rows])
        return simple(cls, data, cls(**data))
    if workload == "post_init_model":
        cls = PostInitDataclass if native else PostInitStruct
        data = {"id": 12345, "name": "  example  "}
        return simple(cls, data, cls(**data), {"id": 12345, "name": "example"})
    if workload == "default_factory_model":
        cls = FactoryDataclass if native else FactoryStruct
        data = {"id": 12345}
        return simple(cls, data, cls(**data), {"id": 12345, "items": []})
    if workload == "recursive_tree_20":
        cls = TreeDataclass if native else TreeStruct
        loaded, data = tree(cls, 20)
        return simple(cls, data, loaded)
    if workload == "tagged_union_1000":
        click, text = (ClickDataclass, TextDataclass) if native else (ClickStruct, TextStruct)
        data = [{"kind": "click", "x": 1000 + i, "y": i} if i % 2 else
                {"kind": "text", "text": f"text_{i}"} for i in range(1000)]
        loaded = [(click if row["kind"] == "click" else text)(**(row if native else
                   {key: value for key, value in row.items() if key != "kind"})) for row in data]
        return simple(list[click | text], data, loaded)
    if workload == "wide_model_128":
        cls = WideDataclass if native else WideStruct
        data = {name: 1000 + i for i, (name, _) in enumerate(WIDE_FIELDS)}
        return simple(cls, data, cls(**data))
    if workload == "book_fresh_keys_100":
        data = create_dumped_book(reviews_count=100)
        data = {key.encode().decode(): value for key, value in data.items()}
        data["reviews"] = [{key.encode().decode(): value for key, value in row.items()} for row in data["reviews"]]
        book, review = (
            (bench_adaptix.Book, bench_adaptix.Review) if native else (bench_msgspec.Book, bench_msgspec.Review)
        )
        if native:
            retort = bench_adaptix.retort.replace(codegen_backend=CodeGenBackend.X86_64)
        return matrix.Case(book, data, create_book(book, review, reviews_count=100), data, retort)
    if workload == "book_1000":
        return matrix.create_case(workload, implementation)
    raise ValueError(workload)


def bench_loading(implementation, workload):
    case = create_case(workload, implementation)
    plan = (
        benchmark_plan(case.retort.get_loader(case.target), case.load_input) if implementation == "adaptix_x86_64" else
        benchmark_plan(msgspec.convert, case.load_input, case.target)
    )
    assert plan.func(*plan.args) == case.loaded
    return plan


def bench_dumping(implementation, workload):
    case = create_case(workload, implementation)
    function = case.retort.get_dumper(case.target) if implementation == "adaptix_x86_64" else msgspec.to_builtins
    plan = benchmark_plan(function, case.loaded)
    assert plan.func(*plan.args) == case.dumped
    return plan


def reject(function, *args):
    try:
        function(*args)
    except (LoadError, msgspec.ValidationError):
        return True
    raise AssertionError("Invalid input was accepted")


def bench_error(implementation, workload, debug_trail):
    native = implementation == "adaptix_x86_64"
    if workload.startswith("list_"):
        target = list[int]
        data = list(range(1000, 2000))
        if workload == "list_bad_all":
            data = ["bad"] * 1000
        else:
            data[0 if workload == "list_bad_first" else -1] = "bad"
        retort = create_retort(
            DebugTrail(debug_trail),
            codegen_backend=CodeGenBackend.X86_64 if native else CodeGenBackend.PYTHON,
        )
    else:
        case = matrix.create_case("flat_model", implementation)
        target, data = case.target, dict(case.load_input)
        if workload == "model_bad_field":
            data["id"] = "bad"
        else:
            del data["id"]
        retort = case.retort.replace(debug_trail=DebugTrail(debug_trail))
    plan = (
        benchmark_plan(reject, retort.get_loader(target), data) if native else
        benchmark_plan(reject, msgspec.convert, data, target)
    )
    assert plan.func(*plan.args) is True
    return plan


def json_load(data, decode, load):
    return load(decode(data))


def json_dump(value, dump, encode):
    return encode(dump(value))


def stdlib_encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def bench_json(implementation, workload, operation):
    native = implementation != "msgspec"
    case = matrix.create_case(workload, "adaptix_x86_64" if native else "msgspec")
    source = msgspec.json.encode(case.load_input)
    if operation == "loading":
        if native:
            decode = msgspec.json.Decoder().decode if implementation == "adaptix_msgspec_json" else json.loads
            plan = benchmark_plan(json_load, source, decode, case.retort.get_loader(case.target))
        else:
            plan = benchmark_plan(msgspec.json.Decoder(case.target).decode, source)
        assert plan.func(*plan.args) == case.loaded
    else:
        if native:
            encode = msgspec.json.Encoder().encode if implementation == "adaptix_msgspec_json" else stdlib_encode
            plan = benchmark_plan(json_dump, case.loaded, case.retort.get_dumper(case.target), encode)
        else:
            plan = benchmark_plan(msgspec.json.Encoder().encode, case.loaded)
        assert msgspec.json.decode(plan.func(*plan.args)) == case.dumped
    return plan


def fresh_native_json(data, target):
    retort = Retort(
        recipe=[name_mapping(bench_adaptix.Review, map={"content": "text"})],
        codegen_backend=CodeGenBackend.X86_64,
        strict_coercion=True,
        debug_trail=DebugTrail.ALL,
    )
    load = retort.get_loader(target)
    return load(msgspec.json.Decoder().decode(data))


def fresh_msgspec_json(data, target):
    return msgspec.json.Decoder(target).decode(data)


def bench_fresh_converter(implementation, workload):
    case = matrix.create_case(workload, implementation)
    function = fresh_native_json if implementation == "adaptix_x86_64" else fresh_msgspec_json
    plan = benchmark_plan(function, msgspec.json.encode(case.load_input), case.target)
    assert plan.func(*plan.args) == case.loaded
    return plan


STARTUP_NATIVE = """
from dataclasses import dataclass
from adaptix import Retort, CodeGenBackend
@dataclass
class Model:
    id: int
    name: str
    score: float
    active: bool
value = Retort(codegen_backend=CodeGenBackend.X86_64).load(
    {"id": 12345, "name": "example", "score": 1.25, "active": True}, Model,
)
assert value.id == 12345 and value.name == "example" and value.score == 1.25 and value.active is True
"""
STARTUP_MSGSPEC = """
import msgspec
class Model(msgspec.Struct):
    id: int
    name: str
    score: float
    active: bool
value = msgspec.convert({"id": 12345, "name": "example", "score": 1.25, "active": True}, Model)
assert value.id == 12345 and value.name == "example" and value.score == 1.25 and value.active is True
"""


def startup(program):
    subprocess.run([sys.executable, "-c", program], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)  # noqa: S603
    return True


def bench_startup(implementation):
    plan = benchmark_plan(startup, STARTUP_NATIVE if implementation == "adaptix_x86_64" else STARTUP_MSGSPEC)
    assert plan.func(*plan.args)
    return plan


def check_platform():
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
@pytest.mark.parametrize("workload", WORKLOADS)
def test_round_trip(implementation, workload):
    if implementation == "adaptix_x86_64":
        check_platform()
    case = create_case(workload, implementation)
    loading = bench_loading(implementation, workload)
    dumping = bench_dumping(implementation, workload)
    assert loading.func(*loading.args) == case.loaded
    assert dumping.func(*dumping.args) == case.dumped


@pytest.mark.parametrize(
    ["implementation", "debug_trail"],
    [("adaptix_x86_64", "ALL"), ("adaptix_x86_64", "FIRST"), ("msgspec", "FIRST")],
)
@pytest.mark.parametrize("workload", ERROR_WORKLOADS)
def test_rejection(implementation, debug_trail, workload):
    if implementation == "adaptix_x86_64":
        check_platform()
    plan = bench_error(implementation, workload, debug_trail)
    assert plan.func(*plan.args)


@pytest.mark.parametrize("implementation", ["adaptix_msgspec_json", "adaptix_stdlib_json", "msgspec"])
@pytest.mark.parametrize("workload", JSON_WORKLOADS)
@pytest.mark.parametrize("operation", ["loading", "dumping"])
def test_json(implementation, workload, operation):
    if implementation != "msgspec":
        check_platform()
    bench_json(implementation, workload, operation)


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
@pytest.mark.parametrize("workload", JSON_WORKLOADS)
def test_fresh_converter(implementation, workload):
    if implementation == "adaptix_x86_64":
        check_platform()
    bench_fresh_converter(implementation, workload)


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_startup(implementation):
    if implementation == "adaptix_x86_64":
        check_platform()
    bench_startup(implementation)
