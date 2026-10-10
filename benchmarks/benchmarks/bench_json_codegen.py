# ruff: noqa: S101
import json
import random

import msgspec
import pytest

from adaptix import CodeGenBackend
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix.json import JsonRetort, StdlibJsonCodec
from benchmarks.bench_backend_matrix import WORKLOADS as MATRIX_WORKLOADS, Case, create_case as matrix_case
from benchmarks.bench_backend_stress import create_case as stress_case
from benchmarks.pybench.bench_api import benchmark_plan

WORKLOADS = (
    *MATRIX_WORKLOADS,
    "list_float_1000",
    "list_float_random_1000",
    "list_str_unicode_1000",
    "list_union_int_str_1000",
    "recursive_tree_20",
    "escaped_model",
    "reordered_model",
)
IMPLEMENTATIONS = ("adaptix_native_json", "adaptix_stdlib_json", "adaptix_python_json", "msgspec")
FORMATS = ("bytes", "str")
OPERATIONS = ("loading", "dumping")


def create_case(workload, implementation):
    competitor = implementation == "msgspec"
    backend = "msgspec" if competitor else "adaptix_x86_64"
    codegen_backend = CodeGenBackend.PYTHON if implementation == "adaptix_python_json" else None
    if workload in MATRIX_WORKLOADS:
        case = matrix_case(workload, backend, codegen_backend=codegen_backend)
    elif workload == "list_float_random_1000":
        base = stress_case("list_float_1000", backend, codegen_backend=codegen_backend)
        randomizer = random.Random(2026)  # noqa: S311
        data = [randomizer.uniform(-1e6, 1e6) for _ in range(1000)]
        case = Case(base.target, data, data, data, base.retort)
    elif workload in ("escaped_model", "reordered_model"):
        case = matrix_case("flat_model", backend, codegen_backend=codegen_backend)
        data = dict(case.load_input)
        if workload == "escaped_model":
            data["text"] = 'Line 1\nLine 2\t"quoted"\\path 😀'
        else:
            data = dict(reversed(list(data.items())))
        loaded = msgspec.convert(data, case.target) if competitor else case.retort.load(data, case.target)
        case = Case(case.target, data, loaded, data, case.retort)
    else:
        case = stress_case(workload, backend, codegen_backend=codegen_backend)
    return case


def bench_json(implementation: str, workload: str, operation: str, data_format: str):
    case = create_case(workload, implementation)
    if implementation == "msgspec":
        if operation == "loading":
            function = msgspec.json.Decoder(case.target).decode
        elif data_format == "bytes":
            function = msgspec.json.Encoder().encode
        else:
            encode = msgspec.json.Encoder().encode

            def function(data):
                return encode(data).decode("utf-8")
    else:
        codec = None if implementation == "adaptix_native_json" else StdlibJsonCodec()
        facade = JsonRetort(case.retort, codec=codec)
        function = (
            facade.get_loader(case.target)
            if operation == "loading"
            else facade.get_dumper(
                case.target,
                as_bytes=data_format == "bytes",
            )
        )
    if operation == "loading":
        data = msgspec.json.encode(case.load_input)
        if data_format == "str":
            data = data.decode("utf-8")
        plan = benchmark_plan(function, data)
        assert plan.func(*plan.args) == case.loaded
    else:
        plan = benchmark_plan(function, case.loaded)
        result = plan.func(*plan.args)
        assert isinstance(result, bytes if data_format == "bytes" else str)
        assert json.loads(result) == case.dumped
    return plan


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("data_format", FORMATS)
def test_benchmark(implementation, workload, operation, data_format):
    if implementation.startswith("adaptix") and implementation != "adaptix_python_json":
        try:
            check_native_platform()
        except RuntimeError as error:
            pytest.skip(str(error))
    bench_json(implementation, workload, operation, data_format)
