# ruff: noqa: S101
from dataclasses import dataclass, fields, is_dataclass, make_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, IntEnum
from functools import lru_cache
from itertools import combinations
from typing import Any, Literal, NamedTuple, TypedDict
from uuid import UUID

import msgspec
import pytest

from adaptix import CodeGenBackend, DebugTrail, Retort
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from benchmarks.pybench.bench_api import benchmark_plan


class Colour(str, Enum):
    RED = "red"
    BLUE = "blue"


class Number(IntEnum):
    ONE = 1
    TWO = 2


class Pair(NamedTuple):
    id: int
    name: str


class Record(TypedDict):
    id: int
    values: list[int | str | None]


@dataclass(frozen=True)
class Atom:
    target: Any
    values: tuple


ATOMS = {
    "int": Atom(int, (1000, 2000)),
    "big_int": Atom(int, (2**100, -(2**100))),
    "str": Atom(str, ("example", "another")),
    "unicode": Atom(str, ("строка_日本語_🙂", "другая_😀")),
    "long_str": Atom(str, ("x" * 4096, "🙂" * 1024)),
    "float": Atom(float, (1.25, -2.5)),
    "float_from_int": Atom(float, (1000, 2000)),
    "bool": Atom(bool, (True, False)),
    "none": Atom(type(None), (None,)),
    "any": Atom(Any, (1000, "example", None, {"nested": [1, 2]})),
    "optional_int": Atom(int | None, (1000, None, 2000)),
    "optional_str": Atom(str | None, ("example", None, "another")),
    "union_int_str": Atom(int | str, (1000, "example", 2000)),
    "union_int_str_only_int": Atom(int | str, (1000, 2000)),
    "union_int_str_only_str": Atom(int | str, ("example", "another")),
    "union_bool_str": Atom(bool | str, (True, "example", False)),
    "union_int_bool": Atom(int | bool, (1000, True, False)),
    "union_float_str": Atom(float | str, (1.25, "example", -2.5)),
    "union_float_str_from_int": Atom(float | str, (1000, "example", 2000)),
    "union_int_float": Atom(int | float, (1000, 1.25, 2000)),
    "union_optional_int_str": Atom(int | str | None, (1000, "example", None)),
    "union_optional_int_str_only_none": Atom(int | str | None, (None,)),
    "union_int_str_bool": Atom(int | str | bool, (1000, "example", True, False)),
    "union_all_scalars": Atom(int | str | bool | float | None, (1000, "example", True, 1.25, None)),
    "literal_str": Atom(Literal["red", "blue"], ("red", "blue")),
    "literal_int": Atom(Literal[1000, 2000], (1000, 2000)),
    "literal_bool": Atom(Literal[True, False], (True, False)),
    "enum_str": Atom(Colour, ("red", "blue")),
    "enum_int": Atom(Number, (1, 2)),
    "decimal": Atom(Decimal, ("1000.125", "-2000.25")),
    "uuid": Atom(UUID, (str(UUID(int=1000)), str(UUID(int=2000)))),
    "bytes": Atom(bytes, ("YWJjAP8=", "YW5vdGhlcg==")),
    "date": Atom(date, ("2025-01-02", "2025-03-04")),
    "time": Atom(time, ("03:04:05.001000", "06:07:08.002000")),
    "datetime": Atom(datetime, ("2025-01-02T03:04:05.001000", "2025-03-04T06:07:08.002000")),
    "datetime_utc": Atom(datetime, ("2025-01-02T03:04:05+00:00", "2025-03-04T06:07:08+00:00")),
    "datetime_offset": Atom(datetime, ("2025-01-02T03:04:05+05:30", "2025-03-04T06:07:08-04:00")),
    "timedelta": Atom(timedelta, (1.25, 1000.5)),
    "optional_decimal": Atom(Decimal | None, ("1000.125", None, "-2000.25")),
    "optional_enum": Atom(Colour | None, ("red", None, "blue")),
    "optional_date": Atom(date | None, ("2025-01-02", None, "2025-03-04")),
    "optional_bytes": Atom(bytes | None, ("YWJjAP8=", None, "YW5vdGhlcg==")),
    "union_list_str": Atom(list[int] | str, ([1000, 2000], "example")),
    "union_list_dict": Atom(list[int] | dict[str, int], ([1000, 2000], {"key": 1000})),
    "union_bytes_str": Atom(bytes | str, ("YWJjAP8=", "YW5vdGhlcg==")),
    "union_enum_str": Atom(Colour | str, ("red", "other")),
}
SHAPES = (
    "scalar", "list", "tuple", "fixed_tuple", "dict", "nested_list", "dict_list", "list_dict",
    "model", "model_dataclass",
)
SIZED_ATOMS = (
    "int", "float", "float_from_int", "str", "any", "optional_int", "union_int_str",
    "union_optional_int_str", "union_float_str", "union_int_float", "literal_str", "enum_str",
)
SET_ATOMS = ("int", "str", "optional_int", "union_int_str", "union_optional_int_str", "decimal", "enum_str")
INPUT_SHAPES = ("tuple_input", "set_input", "list_subclass", "dict_subclass")
MODEL_CLASSES = {
    name: (
        make_dataclass(f"Model_{name}", [("value", atom.target)], namespace={"__module__": __name__}),
        msgspec.defstruct(f"Struct_{name}", [("value", atom.target)], module=__name__),
    )
    for name, atom in ATOMS.items()
}


class ListSubclass(list):
    pass


class DictSubclass(dict):
    pass


@dataclass(frozen=True)
class Workload:
    atom: str
    shape: str
    size: int


WORKLOADS = {
    f"{shape}_{name}_{size}": Workload(name, shape, size)
    for name in ATOMS
    for shape in SHAPES
    for size in ((1,) if shape == "scalar" else (1000,) if shape != "fixed_tuple" else (3,))
}
WORKLOADS.update({
    f"{shape}_{name}_{size}": Workload(name, shape, size)
    for name in SIZED_ATOMS for shape in ("list", "dict") for size in (0, 1, 10)
})
WORKLOADS.update({
    f"{shape}_{name}_1000": Workload(name, shape, 1000)
    for name in SET_ATOMS for shape in ("set", "frozenset")
})
WORKLOADS.update({
    f"{shape}_{name}_1000": Workload(name, shape, 1000)
    for name in ("int", "union_int_str", "union_optional_int_str", "float_from_int") for shape in INPUT_SHAPES
})
WORKLOADS.update({
    f"dict_keys_{name}_1000": Workload(name, "dict_keys", 1000)
    for name in ("int", "str", "float", "bool", "union_int_str", "literal_str", "enum_str", "uuid")
})
WORKLOADS.update({
    "named_tuple": Workload("int", "named_tuple", 1),
    "typed_dict": Workload("int", "typed_dict", 1),
})
IMPLEMENTATIONS = ("adaptix_x86_64", "msgspec")


def register_atom_workloads(name, atom):
    ATOMS[name] = atom
    MODEL_CLASSES[name] = (
        make_dataclass(f"Model_{name}", [("value", atom.target)], namespace={"__module__": __name__}),
        msgspec.defstruct(f"Struct_{name}", [("value", atom.target)], module=__name__),
    )
    for shape in SHAPES:
        count = 1 if shape == "scalar" else 3 if shape == "fixed_tuple" else 1000
        WORKLOADS[f"{shape}_{name}_{count}"] = Workload(name, shape, count)


def expand_scalar_unions():
    scalars = (("int", int, 1000), ("str", str, "example"), ("bool", bool, True),
               ("float", float, 1.25), ("none", type(None), None))
    existing = {atom.target for atom in ATOMS.values()}
    for size in range(2, len(scalars) + 1):
        for options in combinations(scalars, size):
            target = options[0][1]
            for _, cls, _ in options[1:]:
                target |= cls
            name = "scalar_union_" + "_".join(option[0] for option in options)
            # Existing mixed workloads already cover some unions. Add every
            # missing combination and test every scalar branch individually.
            if target not in existing:
                register_atom_workloads(name, Atom(target, tuple(option[2] for option in options)))
                existing.add(target)
            for branch, _, value in options:
                branch_name = f"{name}_branch_{branch}"
                ATOMS[branch_name] = Atom(target, (value,))
                WORKLOADS[f"scalar_{branch_name}_1"] = Workload(branch_name, "scalar", 1)
            if any(cls is float for _, cls, _ in options) and not any(cls is int for _, cls, _ in options):
                register_atom_workloads(f"{name}_from_int", Atom(target, (1000, 2000)))


@lru_cache
def create_retort(implementation, debug_trail="ALL", *, strict_coercion=True):
    return Retort(
        codegen_backend=CodeGenBackend.X86_64 if implementation == "adaptix_x86_64" else CodeGenBackend.PYTHON,
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail(debug_trail),
    )


def create_input(workload, implementation):  # noqa: C901, PLR0911, PLR0912
    spec = WORKLOADS[workload]
    atom = ATOMS[spec.atom]
    values = [atom.values[index % len(atom.values)] for index in range(spec.size)]
    if spec.shape == "scalar":
        return atom.target, values[0]
    if spec.shape in {"list", "tuple_input", "set_input", "list_subclass"}:
        data = {
            "list": list, "tuple_input": tuple, "set_input": set, "list_subclass": ListSubclass,
        }[spec.shape](values)
        return list[atom.target], data
    if spec.shape == "tuple":
        return tuple[atom.target, ...], values
    if spec.shape == "fixed_tuple":
        return tuple[(atom.target,) * spec.size], values
    if spec.shape in {"set", "frozenset"}:
        return (set if spec.shape == "set" else frozenset)[atom.target], values
    if spec.shape in {"dict", "dict_subclass"}:
        cls = dict if spec.shape == "dict" else DictSubclass
        return dict[str, atom.target], cls((f"key_{index}", value) for index, value in enumerate(values))
    if spec.shape == "dict_keys":
        return dict[atom.target, str], {value: f"value_{index}" for index, value in enumerate(values)}
    if spec.shape == "nested_list":
        return list[list[atom.target]], [values[index:index + 10] for index in range(0, spec.size, 10)]
    if spec.shape == "dict_list":
        return dict[str, list[atom.target]], {
            f"key_{index}": values[index:index + 10] for index in range(0, spec.size, 10)
        }
    if spec.shape == "list_dict":
        return list[dict[str, atom.target]], [
            {f"key_{index}": value for index, value in enumerate(values[start:start + 10])}
            for start in range(0, spec.size, 10)
        ]
    if spec.shape in {"model", "model_dataclass"}:
        cls = MODEL_CLASSES[spec.atom][implementation == "msgspec" and spec.shape == "model"]
        return list[cls], [{"value": value} for value in values]
    if spec.shape == "named_tuple":
        return Pair, {"id": 1000, "name": "example"}
    if spec.shape == "typed_dict":
        return Record, {"id": 1000, "values": [1000, "example", None]}
    raise ValueError(spec.shape)


def canonical(value):  # noqa: PLR0911
    # Keep primitive types: Python equality alone treats True, 1, and 1.0 as equal.
    if is_dataclass(value):
        return ("model", tuple((field.name, canonical(getattr(value, field.name))) for field in fields(value)))
    if isinstance(value, msgspec.Struct):
        return ("model", tuple((name, canonical(getattr(value, name))) for name in value.__struct_fields__))
    if isinstance(value, dict):
        return ("dict", tuple(sorted(((canonical(key), canonical(item)) for key, item in value.items()), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(canonical(item) for item in value))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted((canonical(item) for item in value), key=repr)))
    if isinstance(value, (datetime, time)):
        return (type(value).__name__, value.isoformat(), value.fold)
    return (type(value).__qualname__, value)


def result_signature(workload, operation, result):
    spec = WORKLOADS[workload]
    if operation == "dumping" and spec.shape in {"set", "frozenset"}:
        return ("unordered_list", tuple(sorted((canonical(item) for item in result), key=repr)))
    return canonical(result)


def create_plan(implementation, workload, operation, debug_trail="ALL"):
    target, data = create_input(workload, implementation)
    if implementation == "msgspec":
        if operation == "loading":
            return benchmark_plan(msgspec.convert, data, target)
        return benchmark_plan(msgspec.to_builtins, msgspec.convert(data, target))
    retort = create_retort(implementation, debug_trail)
    if operation == "loading":
        return benchmark_plan(retort.get_loader(target), data)
    loaded = create_retort("adaptix_python").get_loader(target)(data)
    return benchmark_plan(retort.get_dumper(target), loaded)


def bench_loading(implementation, workload):
    plan = create_plan(implementation, workload, "loading")
    plan.func(*plan.args)
    return plan


def bench_dumping(implementation, workload):
    plan = create_plan(implementation, workload, "dumping")
    plan.func(*plan.args)
    return plan


@lru_cache
def supports_comparison(workload, operation):
    try:
        python = create_plan("adaptix_python", workload, operation)
        other = create_plan("msgspec", workload, operation)
        return result_signature(workload, operation, python.func(*python.args)) == result_signature(
            workload, operation, other.func(*other.args),
        )
    except Exception:
        return False


@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("operation", ["loading", "dumping"])
def test_native_matches_python(workload, operation):
    try:
        check_native_platform()
    except RuntimeError as error:
        pytest.skip(str(error))
    python = create_plan("adaptix_python", workload, operation)
    expected = python.func(*python.args)
    native = create_plan("adaptix_x86_64", workload, operation)
    actual = native.func(*native.args)
    assert result_signature(workload, operation, actual) == result_signature(workload, operation, expected)
