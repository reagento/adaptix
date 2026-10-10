import platform
import sys
import sysconfig

from adaptix import CodeGenBackend, DebugTrail
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams
from benchmarks.simple_structures import bench_codegen


def skip_native(env_spec):
    return (
        env_spec["py_impl"] != "cpython"
        or env_spec["os"] != "linux"
        or env_spec["arch"] not in {"x86_64", "amd64"}
        or env_spec["gil"] != "enabled"
    )


director = BenchmarkDirector(
    benchmark="simple_structures/codegen",
    env_spec={
        "py": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "py_impl": sys.implementation.name,
        "os": sys.platform,
        "arch": platform.machine().lower(),
        "gil": "disabled" if sysconfig.get_config_var("Py_GIL_DISABLED") else "enabled",
    },
    check_params=lambda env_spec: CheckParams(stdev_rel_threshold=0.04),
)

for operation, entry_point in (
    ("loading", bench_codegen.bench_loading),
    ("dumping", bench_codegen.bench_dumping),
):
    workloads = (
        ("flat", "nested", "nested_fresh_keys", "nested_slots", "nested_diverse") if operation == "loading" else
        ("flat", "nested", "nested_slots", "nested_polymorphic", "nested_diverse")
    )
    for workload in workloads:
        trails = DebugTrail if workload in {"flat", "nested"} else (DebugTrail.ALL,)
        for debug_trail in trails:
            for backend in CodeGenBackend:
                director.add(
                    BenchSchema(
                        entry_point=entry_point,
                        base="adaptix",
                        tags=[operation, workload, backend.value, f"dt_{debug_trail.value}"],
                        kwargs={
                            "codegen_backend": backend.value,
                            "debug_trail": debug_trail.value,
                            "workload": workload,
                        },
                        used_distributions=["adaptix"],
                        skip_if=skip_native if backend == CodeGenBackend.X86_64 else None,
                    ),
                )

for operation in ("loading", "dumping"):
    for workload in ("flat", "nested", "shared_graph"):
        for backend in CodeGenBackend:
            director.add(
                BenchSchema(
                    entry_point=bench_codegen.bench_creation,
                    base="adaptix",
                    tags=[f"creation_{operation}", workload, backend.value],
                    kwargs={
                        "operation": operation,
                        "workload": workload,
                        "codegen_backend": backend.value,
                        "debug_trail": DebugTrail.ALL.value,
                    },
                    used_distributions=["adaptix"],
                    skip_if=skip_native if backend == CodeGenBackend.X86_64 else None,
                ),
            )

if __name__ == "__main__":
    director.cli()
