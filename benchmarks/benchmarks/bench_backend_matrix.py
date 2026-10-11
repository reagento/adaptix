# ruff: noqa: S101
from dataclasses import dataclass, make_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import msgspec
import pytest

from adaptix import CodeGenBackend, DebugTrail, Retort
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from benchmarks.gh_issues import bench_adaptix as gh_adaptix, bench_msgspec as gh_msgspec
from benchmarks.gh_issues.common import create_dumped_response, create_response
from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures import bench_adaptix as simple_adaptix, bench_msgspec as simple_msgspec
from benchmarks.simple_structures.common import create_book, create_dumped_book


class State(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


WIDE_FIELDS = [(f"field_{index}", int) for index in range(32)]
WideDataclass = make_dataclass("WideDataclass", WIDE_FIELDS, namespace={"__module__": __name__})
WideStruct = msgspec.defstruct("WideStruct", WIDE_FIELDS, module=__name__)
WideStructNoGC = msgspec.defstruct("WideStructNoGC", WIDE_FIELDS, module=__name__, gc=False)


@dataclass
class DefaultsDataclass:
    id: int
    name: str
    rating: float = 0.0
    comment: str | None = None


class DefaultsStruct(msgspec.Struct):
    id: int
    name: str
    rating: float = 0.0
    comment: str | None = None


class DefaultsStructNoGC(msgspec.Struct, gc=False):
    id: int
    name: str
    rating: float = 0.0
    comment: str | None = None


WORKLOADS = (
    "scalar_int", "flat_model", "wide_model", "defaults_model",
    "book_0", "book_1", "book_100",
    "list_int_1000", "dict_str_int_1000", "list_optional_int_1000",
    "list_enum_1000", "list_datetime_100", "nested_lists", "github_issues",
)
MODEL_WORKLOADS = {
    "flat_model", "wide_model", "defaults_model", "book_0", "book_1", "book_100", "github_issues",
}
IMPLEMENTATIONS = ("adaptix_x86_64", "msgspec", "msgspec_no_gc")


@dataclass
class Case:
    target: Any
    load_input: Any
    loaded: Any
    dumped: Any
    retort: Retort


def create_case(workload: str, implementation: str) -> Case:  # noqa: C901, PLR0911, PLR0912
    native = implementation == "adaptix_x86_64"
    no_gc = implementation == "msgspec_no_gc"
    retort = Retort(
        codegen_backend=CodeGenBackend.X86_64 if native else CodeGenBackend.PYTHON,
        strict_coercion=True,
        debug_trail=DebugTrail.ALL,
    )
    if workload == "scalar_int":
        return Case(int, 12345, 12345, 12345, retort)
    if workload == "wide_model":
        cls = WideDataclass if native else (WideStructNoGC if no_gc else WideStruct)
        data = {name: 1000 + index for index, (name, _) in enumerate(WIDE_FIELDS)}
        return Case(cls, data, cls(**data), data, retort)
    if workload == "defaults_model":
        cls = DefaultsDataclass if native else (DefaultsStructNoGC if no_gc else DefaultsStruct)
        data = {"id": 12345, "name": "example"}
        dumped = {**data, "rating": 0.0, "comment": None}
        return Case(cls, data, cls(**data), dumped, retort)
    if workload == "flat_model" or workload.startswith("book_"):
        count = 1 if workload == "flat_model" else int(workload.split("_")[1])
        if native:
            book_cls, review_cls = simple_adaptix.Book, simple_adaptix.Review
            retort = simple_adaptix.retort.replace(codegen_backend=CodeGenBackend.X86_64)
        elif no_gc:
            book_cls, review_cls = simple_msgspec.BookNoGC, simple_msgspec.ReviewNoGC
        else:
            book_cls, review_cls = simple_msgspec.Book, simple_msgspec.Review
        data = create_dumped_book(reviews_count=count)
        loaded = create_book(book_cls, review_cls, reviews_count=count)
        if workload == "flat_model":
            return Case(review_cls, data["reviews"][0], loaded.reviews[0], data["reviews"][0], retort)
        return Case(book_cls, data, loaded, data, retort)
    if workload == "github_issues":
        module = gh_adaptix if native else gh_msgspec
        suffix = "NoGC" if no_gc else ""
        classes = [
            getattr(module, name + suffix)
            for name in ("GetRepoIssuesResponse", "Issue", "Reactions", "PullRequest", "Label", "SimpleUser")
        ]
        data = create_dumped_response()
        if native:
            retort = gh_adaptix.retort.replace(codegen_backend=CodeGenBackend.X86_64)
        return Case(classes[0], data, create_response(*classes), data, retort)
    if workload == "list_int_1000":
        data = list(range(1000, 2000))
        return Case(list[int], data, data, data, retort)
    if workload == "dict_str_int_1000":
        data = {f"key_{index}": 1000 + index for index in range(1000)}
        return Case(dict[str, int], data, data, data, retort)
    if workload == "list_optional_int_1000":
        data = [None if index % 4 == 0 else 1000 + index for index in range(1000)]
        return Case(list[int | None], data, data, data, retort)
    if workload == "list_enum_1000":
        data = ["open" if index % 2 else "closed" for index in range(1000)]
        return Case(list[State], data, [State(value) for value in data], data, retort)
    if workload == "list_datetime_100":
        loaded = [datetime(2025, 1, 2, 3, 4, 5, 1000 + index) for index in range(100)]  # noqa: DTZ001
        data = [value.isoformat() for value in loaded]
        return Case(list[datetime], data, loaded, data, retort)
    if workload == "nested_lists":
        data = [list(range(1000 + index * 50, 1050 + index * 50)) for index in range(20)]
        return Case(list[list[int]], data, data, data, retort)
    raise ValueError(f"Unknown workload: {workload}")


def bench_loading(implementation: str, workload: str):
    case = create_case(workload, implementation)
    if implementation == "adaptix_x86_64":
        plan = benchmark_plan(case.retort.get_loader(case.target), case.load_input)
    else:
        # convert defaults to strict=True. Call the C function directly so the
        # comparison does not add a Python wrapper or functools.partial overhead.
        plan = benchmark_plan(msgspec.convert, case.load_input, case.target)
    assert plan.func(*plan.args) == case.loaded
    return plan


def bench_dumping(implementation: str, workload: str):
    case = create_case(workload, implementation)
    function = case.retort.get_dumper(case.target) if implementation == "adaptix_x86_64" else msgspec.to_builtins
    plan = benchmark_plan(function, case.loaded)
    assert plan.func(*plan.args) == case.dumped
    return plan


@pytest.mark.parametrize(
    ["implementation", "workload"],
    [
        (implementation, workload)
        for workload in WORKLOADS
        for implementation in IMPLEMENTATIONS
        if implementation != "msgspec_no_gc" or workload in MODEL_WORKLOADS
    ],
)
def test_round_trip(implementation, workload):
    if implementation == "adaptix_x86_64":
        try:
            check_native_platform()
        except RuntimeError as error:
            pytest.skip(str(error))
    case = create_case(workload, implementation)
    loader = bench_loading(implementation, workload)
    dumper = bench_dumping(implementation, workload)
    result = loader.func(*loader.args)
    assert result == case.loaded
    assert dumper.func(*dumper.args) == case.dumped
    if implementation == "msgspec_no_gc":
        assert type(result).__struct_config__.gc is False
    if implementation == "adaptix_x86_64":
        assert case.retort.get_dumper(case.target)(result) == case.dumped
    else:
        assert msgspec.to_builtins(result) == case.dumped
