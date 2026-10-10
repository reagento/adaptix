import csv
import gc
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import timeit
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

import msgspec

import adaptix
from adaptix import CodeGenBackend
from benchmarks import bench_backend_matrix as matrix, bench_backend_stress as stress, bench_backend_types as types
from benchmarks.pybench.bench_api import benchmark_plan

MODULES = {"matrix": matrix, "stress": stress, "types": types}
SCREENING_FACTOR = 1.1


@dataclass(frozen=True)
class Entry:
    suite: str
    workload: str
    operation: str
    mode: str = "cached"
    debug_trail: str = "ALL"
    competitor: str = "msgspec"

    @property
    def name(self):
        return f"{self.suite}/{self.mode}/{self.operation}/{self.workload}/{self.debug_trail}/{self.competitor}"


def entries():
    result = [
        Entry(suite, workload, operation)
        for suite, module in MODULES.items()
        for workload in module.WORKLOADS
        for operation in ("loading", "dumping")
    ]
    result.extend(
        Entry("matrix", workload, operation, competitor="msgspec_no_gc")
        for workload in sorted(matrix.MODEL_WORKLOADS) for operation in ("loading", "dumping")
    )
    result.extend(
        Entry("stress", workload, "loading", "error", trail)
        for workload in stress.ERROR_WORKLOADS for trail in ("DISABLE", "FIRST", "ALL")
    )
    for workload in stress.JSON_WORKLOADS:
        for operation in ("loading", "dumping"):
            result.extend(Entry("stress", workload, operation, mode) for mode in ("json_msgspec", "json_stdlib"))
        result.append(Entry("stress", workload, "loading", "fresh"))
    result.append(Entry("stress", "import_and_first_load", "loading", "startup"))
    for workload in ("scalar_int", "flat_model", "book_100", "list_int_1000", "github_issues"):
        result.extend(Entry("matrix", workload, operation, "retort_api") for operation in ("loading", "dumping"))
    for workload in (
        "list_union_int_str_1000", "list_float_from_int_1000", "dict_union_int_str_1000",
        "list_union_list_dict_1000", "model_optional_decimal_1000", "typed_dict",
    ):
        result.extend(Entry("types", workload, operation, "retort_api") for operation in ("loading", "dumping"))
    for workload in (
        "list_int_1000", "list_union_int_str_1000", "list_decimal_1000", "list_datetime_offset_1000",
        "model_union_optional_int_str_1000", "dict_list_int_1000", "list_dict_union_int_str_1000", "typed_dict",
    ):
        result.extend(Entry("types", workload, operation, "json_msgspec") for operation in ("loading", "dumping"))
    # Detect paths depending on exception generation or trail collection even on valid inputs.
    result.extend(
        Entry("types", workload, operation, debug_trail=trail)
        for workload in (
            "list_union_list_dict_1000", "dict_union_int_str_1000", "list_union_int_float_1000",
            "list_union_float_str_from_int_1000", "nested_list_union_optional_int_str_1000",
        )
        for operation in ("loading", "dumping") for trail in ("DISABLE", "FIRST")
    )
    return result


def exception_info(error):
    return {"exception": type(error).__qualname__, "message": str(error)[:2000]}


def fingerprint(result):
    return hashlib.sha256(repr(result).encode()).hexdigest()


def first_difference(expected, actual, path=()):
    if expected == actual:
        return None
    if isinstance(expected, tuple) and isinstance(actual, tuple) and len(expected) == len(actual):
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            if left != right:
                return first_difference(left, right, (*path, index))
    return {"signature_path": path, "adaptix": repr(expected)[:400], "other": repr(actual)[:400]}


def prepare_types(entry):  # noqa: PLR0911
    python = types.create_plan("adaptix_python", entry.workload, entry.operation, entry.debug_trail)
    expected = python.func(*python.args)
    expected_signature = types.result_signature(entry.workload, entry.operation, expected)
    try:
        native = types.create_plan("adaptix_x86_64", entry.workload, entry.operation, entry.debug_trail)
        actual = native.func(*native.args)
    except Exception as error:
        return None, {"status": "native_error", **exception_info(error)}
    actual_signature = types.result_signature(entry.workload, entry.operation, actual)
    if actual_signature != expected_signature:
        return None, {
            "status": "native_mismatch", "expected_sha256": fingerprint(expected_signature),
            "actual_sha256": fingerprint(actual_signature),
            "difference": first_difference(expected_signature, actual_signature),
        }
    try:
        other = types.create_plan("msgspec", entry.workload, entry.operation)
        other_result = other.func(*other.args)
    except Exception as error:
        return None, {"status": "msgspec_error", **exception_info(error)}
    other_signature = types.result_signature(entry.workload, entry.operation, other_result)
    if other_signature != expected_signature:
        return None, {
            "status": "different_semantics", "adaptix_sha256": fingerprint(expected_signature),
            "msgspec_sha256": fingerprint(other_signature),
            "difference": first_difference(expected_signature, other_signature),
        }
    if entry.mode == "retort_api":
        target, data = types.create_input(entry.workload, "adaptix_x86_64")
        retort = types.create_retort("adaptix_x86_64", entry.debug_trail)
        native = benchmark_plan(
            retort.load if entry.operation == "loading" else retort.dump,
            data if entry.operation == "loading" else native.args[0], target,
        )
    elif entry.mode == "json_msgspec":
        target, data = types.create_input(entry.workload, "adaptix_x86_64")
        other_target, _ = types.create_input(entry.workload, "msgspec")
        if entry.operation == "loading":
            source = msgspec.json.encode(data)
            native = benchmark_plan(stress.json_load, source, msgspec.json.Decoder().decode, native.func)
            other = benchmark_plan(msgspec.json.Decoder(other_target).decode, source)
            if types.canonical(native.func(*native.args)) != types.canonical(other.func(*other.args)):
                return None, {"status": "different_semantics", "message": "Typed JSON decoding differs"}
        else:
            native = benchmark_plan(stress.json_dump, native.args[0], native.func, msgspec.json.Encoder().encode)
            other = benchmark_plan(msgspec.json.Encoder().encode, other.args[0])
            if msgspec.json.decode(native.func(*native.args)) != msgspec.json.decode(other.func(*other.args)):
                return None, {"status": "different_semantics", "message": "Typed JSON encoding differs"}
    return (native, other), {"status": "comparable"}


def prepare_existing(entry):
    module = MODULES[entry.suite]
    if entry.mode == "error":
        native = stress.bench_error("adaptix_x86_64", entry.workload, entry.debug_trail)
        other = stress.bench_error("msgspec", entry.workload, "FIRST")
    elif entry.mode.startswith("json_"):
        implementation = "adaptix_msgspec_json" if entry.mode == "json_msgspec" else "adaptix_stdlib_json"
        native = stress.bench_json(implementation, entry.workload, entry.operation)
        other = stress.bench_json("msgspec", entry.workload, entry.operation)
    elif entry.mode == "fresh":
        native = stress.bench_fresh_converter("adaptix_x86_64", entry.workload)
        other = stress.bench_fresh_converter("msgspec", entry.workload)
    elif entry.mode == "startup":
        native = stress.bench_startup("adaptix_x86_64")
        other = stress.bench_startup("msgspec")
    else:
        factory = getattr(module, "bench_" + entry.operation)
        native = factory("adaptix_x86_64", entry.workload)
        other = factory(entry.competitor, entry.workload)
        case = module.create_case(entry.workload, "adaptix_x86_64")
        python_retort = case.retort.replace(codegen_backend=CodeGenBackend.PYTHON)
        if entry.operation == "loading":
            expected = python_retort.get_loader(case.target)(case.load_input)
        else:
            expected = python_retort.get_dumper(case.target)(case.loaded)
        if types.canonical(native.func(*native.args)) != types.canonical(expected):
            return None, {"status": "native_mismatch"}
        if entry.mode == "retort_api":
            native = benchmark_plan(
                case.retort.load if entry.operation == "loading" else case.retort.dump,
                case.load_input if entry.operation == "loading" else case.loaded, case.target,
            )
    return (native, other), {"status": "comparable"}


def prepare(entry):
    try:
        return prepare_types(entry) if entry.suite == "types" else prepare_existing(entry)
    except Exception as error:
        return None, {"status": "preparation_error", **exception_info(error)}


def measure(plan, *, min_time, values, gc_enabled):
    for _ in range(10):
        plan.func(*plan.args)
    timer = timeit.Timer(
        "function(*args)", setup="gc.enable()" if gc_enabled else "pass",
        globals={"function": plan.func, "args": plan.args, "gc": gc},
    )
    loops = 1
    while True:
        duration = timer.timeit(loops)
        if duration >= min_time:
            break
        loops = max(loops * 2, int(loops * min_time / max(duration, 1e-9)))
    gc.collect()
    timings = [timer.timeit(loops) / loops for _ in range(values)]
    return {"values_seconds": timings, "median_seconds": statistics.median(timings), "loops": loops}


def metadata(args):
    source = Path(adaptix.__file__).parent
    return {
        "python": sys.version, "executable": sys.executable, "msgspec": msgspec.__version__,
        "platform": platform.platform(), "machine": platform.machine(), "cpu": args.cpu,
        "gc_enabled": args.gc == "on", "values_per_process": args.values,
        "scalar_unions_expanded": args.scalar_unions,
        "min_time_seconds": args.min_time, "strict_coercion": True,
        "native_source_sha256": fingerprint(tuple(
            (str(path.relative_to(source)), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(source.rglob("*.py"))
        )),
        "argv": sys.argv,
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def worker(args):
    if args.cpu is not None:
        os.sched_setaffinity(0, {args.cpu})
    if args.scalar_unions:
        types.expand_scalar_unions()
    selected = [entry for entry in entries() if not args.filter or args.filter in entry.name]
    if getattr(args, "cached_only", False):
        selected = [entry for entry in selected if entry.mode == "cached"]
    baseline = getattr(args, "baseline_csv", None)
    if baseline is not None:
        with baseline.open() as file:
            names = {row["case"] for row in csv.DictReader(file)
                     if row["status"] == "comparable" and row["screening"] == "adaptix_slower"
                     and (not args.cached_only or row["mode"] == "cached")}
        selected = [entry for entry in selected if entry.name in names]
        missing = names - {entry.name for entry in selected}
        if missing:
            raise ValueError(f"{len(missing)} baseline cases were not found; check --scalar-unions and --filter")
    randomizer = random.Random(20261010 + args.worker)  # noqa: S311
    randomizer.shuffle(selected)
    result = {"metadata": metadata(args), "results": {}}
    for index, entry in enumerate(selected):
        plans, row = prepare(entry)
        if plans is not None and not args.validate_only:
            implementations = [("adaptix_x86_64", plans[0]), (entry.competitor, plans[1])]
            randomizer.shuffle(implementations)
            row["timings"] = {
                name: measure(plan, min_time=args.min_time, values=args.values, gc_enabled=args.gc == "on")
                for name, plan in implementations
            }
            row["adaptix_over_msgspec"] = (
                row["timings"]["adaptix_x86_64"]["median_seconds"]
                / row["timings"][entry.competitor]["median_seconds"]
            )
        result["results"][entry.name] = row
        if (index + 1) % 50 == 0:
            write_json(args.output, result)
            print(f"worker {args.worker}: {index + 1}/{len(selected)}", flush=True)  # noqa: T201
    if metadata(args)["native_source_sha256"] != result["metadata"]["native_source_sha256"]:
        raise RuntimeError("Adaptix source changed during this worker; rerun the audit with a consistent source")
    write_json(args.output, result)


def aggregate(args, workers):
    current_metadata = metadata(args)
    if {result["metadata"]["native_source_sha256"] for result in workers} != {
        current_metadata["native_source_sha256"],
    }:
        raise RuntimeError("Adaptix source changed between workers; rerun the audit with a consistent source")
    rows = {}
    for worker_result in workers:
        for name, result in worker_result["results"].items():
            row = rows.setdefault(name, {"status": result["status"], "workers": []})
            row["workers"].append(result)
    for row in rows.values():
        statuses = {sample["status"] for sample in row["workers"]}
        if len(statuses) != 1:
            row["status"] = "inconsistent_status"
            continue
        ratios = [sample["adaptix_over_msgspec"] for sample in row["workers"] if "adaptix_over_msgspec" in sample]
        if ratios:
            row["ratios"] = ratios
            row["median_ratio"] = statistics.median(ratios)
            if len(ratios) == args.processes and min(ratios) > SCREENING_FACTOR:
                row["screening"] = "adaptix_slower"
            elif len(ratios) == args.processes and max(ratios) < 1 / SCREENING_FACTOR:
                row["screening"] = "adaptix_faster"
            else:
                row["screening"] = "close_or_noisy"
    counts = {status: sum(row["status"] == status for row in rows.values()) for status in sorted({
        row["status"] for row in rows.values()
    })}
    counts.update({status: sum(row.get("screening") == status for row in rows.values()) for status in (
        "adaptix_slower", "adaptix_faster", "close_or_noisy",
    )})
    return {"metadata": current_metadata, "processes": len(workers), "counts": counts, "results": rows}


def main():
    parser = ArgumentParser(description="Screen native Adaptix vs msgspec, preserving errors and semantic differences")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--processes", type=int, default=3)
    parser.add_argument("--values", type=int, default=3)
    parser.add_argument("--min-time", type=float, default=0.01)
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--gc", choices=("on", "off"), default="on")
    parser.add_argument("--filter", default="")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--scalar-unions", action="store_true")
    parser.add_argument("--cached-only", action="store_true")
    parser.add_argument("--baseline-csv", type=Path, help="Measure only stable slow cases from an earlier audit CSV")
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.worker is not None:
        worker(args)
        return
    workers = []
    for index in range(args.processes):
        path = args.output.with_name(f"{args.output.stem}.worker-{index}.json")
        command = [
            sys.executable, "-m", "benchmarks.audit_backend", "--worker", str(index),
            "--output", str(path), "--values", str(args.values), "--min-time", str(args.min_time), "--gc", args.gc,
        ]
        if args.cpu is not None:
            command.extend(("--cpu", str(args.cpu)))
        if args.filter:
            command.extend(("--filter", args.filter))
        if args.validate_only:
            command.append("--validate-only")
        if args.scalar_unions:
            command.append("--scalar-unions")
        if args.cached_only:
            command.append("--cached-only")
        if args.baseline_csv is not None:
            command.extend(("--baseline-csv", str(args.baseline_csv)))
        subprocess.run(command, check=True)  # noqa: S603
        workers.append(json.loads(path.read_text()))
        write_json(args.output, aggregate(args, workers))
    print(json.dumps(aggregate(args, workers)["counts"], indent=2), flush=True)  # noqa: T201


if __name__ == "__main__":
    main()
