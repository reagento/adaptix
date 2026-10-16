import argparse
import gc
import importlib
import json
import os
import resource
import statistics
import subprocess
import sys
import time
from dataclasses import make_dataclass
from pathlib import Path


def memory_kib():
    resident = int(Path("/proc/self/statm").read_text().split()[1])
    return resident * os.sysconf("SC_PAGE_SIZE") // 1024


def probe(backend):
    started = time.perf_counter_ns()
    adaptix = importlib.import_module("adaptix")
    if backend == "llvm2":
        generator = importlib.import_module("adaptix._internal.morphing.native.xdsl.generator")
        codegen = importlib.import_module("adaptix._internal.morphing.native.codegen")
        provider = importlib.import_module("adaptix._internal.provider.value_provider")
        retort = adaptix.Retort(
            recipe=[provider.ValueProvider(codegen.NativeCodeGenRequest, generator.XDSLCodeGenerator())],
        )
    else:
        retort = adaptix.Retort(
            codegen_backend=adaptix.CodeGenBackend.X86_64 if backend == "x86" else adaptix.CodeGenBackend.PYTHON,
        )
    import_ns = time.perf_counter_ns() - started
    gc.collect()
    before = memory_kib()
    model = make_dataclass("Model", [(f"field{i}", int) for i in range(16)], slots=True)
    started = time.perf_counter_ns()
    load = retort.get_loader(model)
    compile_ns = time.perf_counter_ns() - started
    load({f"field{i}": i + 300 for i in range(16)})
    gc.collect()
    live = memory_kib()
    del load, retort, model
    gc.collect()
    return {
        "import_ns": import_ns,
        "compile_ns": compile_ns,
        "before_kib": before,
        "after_kib": live,
        "released_kib": memory_kib(),
        "peak_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", choices=["python", "x86", "llvm2"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cpu", type=int, default=16)
    args = parser.parse_args()
    os.sched_setaffinity(0, {args.cpu})
    if args.probe:
        print(json.dumps(probe(args.probe)))  # noqa: T201
        return
    if args.output is None:
        parser.error("--output is required")
    report = {"python": sys.version, "model": "slots, 16 required int fields", "results": {}}
    for backend in ("python", "x86", "llvm2"):
        samples = [
            # The executable and script are fixed; backend comes from the tuple below.
            json.loads(subprocess.check_output([sys.executable, __file__, "--probe", backend], text=True))  # noqa: S603
            for repeat in range(args.repeats)
        ]
        report["results"][backend] = {
            "median": {key: statistics.median(sample[key] for sample in samples) for key in samples[0]},
            "samples": samples,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
