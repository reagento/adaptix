import argparse
import csv
import gc
import importlib.metadata
import json
import os
import statistics
import time
import timeit
from dataclasses import make_dataclass
from pathlib import Path
from typing import Any

from llvmlite import binding

from adaptix import CodeGenBackend, Retort
from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.morphing.native.codegen import NativeCodeGenRequest
from adaptix._internal.morphing.native.xdsl.compiler import LLVMCode
from adaptix._internal.morphing.native.xdsl.generator import XDSLCodeGenerator
from adaptix._internal.morphing.native.xdsl.reference import ReferenceCodeGenerator
from adaptix._internal.provider.value_provider import ValueProvider


def create_retort(backend, *, capture=False):
    if backend == "python":
        return Retort(), None
    if backend == "x86":
        return Retort(codegen_backend=CodeGenBackend.X86_64), None
    gen = (
        ReferenceCodeGenerator()
        if backend == "reference"
        else XDSLCodeGenerator(
            opt_level=int(backend[-1]),
            capture_artifacts=capture,
        )
    )
    return Retort(recipe=[ValueProvider(NativeCodeGenRequest, gen)]), gen


def scenarios():
    result = [("int", int, 300), ("list_any32", list[Any], list(range(32)))]
    for size in (0, 32, 1024):
        result.append((f"list_int{size}", list[int], list(range(size))))
        result.append(
            (
                f"list_union{size}",
                list[int | str | None],
                [value if value % 3 else str(value) for value in range(size)],
            ),
        )
    for slots in (False, True):
        for size in (4, 16, 64):
            cls = make_dataclass(
                f"Model{size}{'Slots' if slots else 'Dict'}",
                [(f"field{index}", int) for index in range(size)],
                slots=slots,
            )
            data = {f"field{index}": index + 300 for index in range(size)}
            result.append((f"model_{'slots' if slots else 'dict'}{size}", cls, data))
    return result


def save_artifact(path, function):
    if not hasattr(function, "__self__") or not isinstance(function.__self__, NativeCode):
        return None
    code = function.__self__
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".s").write_text(code.assembly)
    if not isinstance(code, LLVMCode):
        path.with_suffix(".bin").write_bytes(code.machine_code)
        return {"text_bytes": len(code.machine_code)}
    artifact = code.memory.artifact
    path.with_suffix(".mlir").write_text(artifact.xdsl_ir)
    path.with_suffix(".ll").write_text(artifact.llvm_ir)
    path.with_suffix(".optimized.ll").write_text(artifact.optimized_ir)
    path.with_suffix(".o").write_bytes(artifact.object_code)
    return {
        "text_bytes": len(artifact.text),
        "object_bytes": len(artifact.object_code),
        "phases_ns": artifact.timings_ns,
    }


def main():  # noqa: C901, PLR0912
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--rounds", type=int, default=9)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--cpu", type=int, default=16)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    os.sched_setaffinity(0, {args.cpu})
    backends = ("python", "x86", "reference", "llvm0", "llvm2", "llvm3")
    report = {
        "python": os.sys.version,
        "xdsl": importlib.metadata.version("xdsl"),
        "llvmlite": importlib.metadata.version("llvmlite"),
        "llvm": binding.llvm_version_info,
        "cpu": binding.get_host_cpu_name(),
        "affinity": list(os.sched_getaffinity(0)),
        "rounds": args.rounds,
        "iterations": args.iterations,
        "results": {},
    }
    cases = scenarios()
    if args.smoke:
        cases = [cases[0], cases[4], cases[8], cases[11]]
    for name, tp, data in cases:
        loaded = Retort().load(data, tp)
        for direction in ("load", "dump"):
            value = data if direction == "load" else loaded
            prepared = {}
            for backend in backends:
                cold = []
                for repeat in range(3):
                    started = time.perf_counter_ns()
                    r = create_retort(backend)[0]
                    function = (r.get_loader if direction == "load" else r.get_dumper)(tp)
                    cold.insert(repeat, time.perf_counter_ns() - started)
                if function(value) != (loaded if direction == "load" else Retort().dump(loaded, tp)):
                    raise RuntimeError(f"Wrong result from {backend} for {name}")
                function(value)
                native = isinstance(getattr(function, "__self__", None), NativeCode)
                prepared[backend] = (function, cold, native)
            samples = {backend: [] for backend in backends}
            for repeat in range(args.rounds):
                order = backends[repeat % len(backends) :] + backends[: repeat % len(backends)]
                for backend in order:
                    function, cold, native = prepared[backend]
                    gc.collect()
                    samples[backend].append(
                        timeit.timeit(
                            "function(value)", globals={"function": function, "value": value}, number=args.iterations,
                        )
                        * 1e9
                        / args.iterations,
                    )
            row = {}
            for backend in backends:
                function, cold, native = prepared[backend]
                row[backend] = {
                    "ns": statistics.median(samples[backend]),
                    "samples_ns": samples[backend],
                    "compile_ns": statistics.median(cold),
                    "compile_samples_ns": cold,
                    "native_root": native,
                }
            if args.artifacts and name in ("list_int1024", "model_slots4", "model_dict64"):
                for backend in ("x86", "reference", "llvm2", "llvm3"):
                    r = create_retort(backend, capture=True)[0]
                    function = (r.get_loader if direction == "load" else r.get_dumper)(tp)
                    row[backend]["quality"] = save_artifact(args.artifacts / f"{name}_{direction}_{backend}", function)
            key = f"{name}/{direction}"
            report["results"][key] = row
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(  # noqa: T201
                f"{key:25} python {row['python']['ns']:9.1f} x86 {row['x86']['ns']:9.1f} "
                f"reference {row['reference']['ns']:9.1f} llvm2 {row['llvm2']['ns']:9.1f} "
                f"llvm3 {row['llvm3']['ns']:9.1f} ns",
                flush=True,
            )
    with args.output.with_suffix(".csv").open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["case", "backend", "ns", "compile_ms", "native_root"])
        for name, row in report["results"].items():
            for backend, data in row.items():
                writer.writerow([name, backend, data["ns"], data["compile_ns"] / 1e6, data["native_root"]])


if __name__ == "__main__":
    main()
