from adaptix import DebugTrail
from benchmarks import bench_backend_stress
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams

director = BenchmarkDirector(
    benchmark="backend_stress",
    env_spec=benchmark_env_spec(),
    check_params=lambda env_spec: CheckParams(stdev_rel_threshold=0.04),
)


def add(entry_point, implementation, tags, **kwargs):
    director.add(
        BenchSchema(
            entry_point=entry_point,
            base=implementation,
            tags=tags,
            kwargs={"implementation": implementation, **kwargs},
            used_distributions=["adaptix", "msgspec"] if implementation.startswith("adaptix") else ["msgspec"],
            skip_if=skip_native if implementation.startswith("adaptix") else None,
        ),
    )


for operation, entry_point in (
    ("loading", bench_backend_stress.bench_loading),
    ("dumping", bench_backend_stress.bench_dumping),
):
    for workload in bench_backend_stress.WORKLOADS:
        for implementation in bench_backend_stress.IMPLEMENTATIONS:
            add(entry_point, implementation, [operation, workload], workload=workload)

for workload in bench_backend_stress.ERROR_WORKLOADS:
    for implementation, trail in (
        ("adaptix_x86_64", DebugTrail.ALL),
        ("adaptix_x86_64", DebugTrail.FIRST),
        ("msgspec", DebugTrail.FIRST),
    ):
        add(
            bench_backend_stress.bench_error, implementation, ["error", workload, trail.value],
            workload=workload, debug_trail=trail.value,
        )

for workload in bench_backend_stress.JSON_WORKLOADS:
    for operation in ("loading", "dumping"):
        for implementation in ("adaptix_msgspec_json", "adaptix_stdlib_json", "msgspec"):
            add(
                bench_backend_stress.bench_json, implementation, ["json", operation, workload],
                workload=workload, operation=operation,
            )
    for implementation in bench_backend_stress.IMPLEMENTATIONS:
        add(
            bench_backend_stress.bench_fresh_converter, implementation, ["fresh_converter", workload],
            workload=workload,
        )

for implementation in bench_backend_stress.IMPLEMENTATIONS:
    add(bench_backend_stress.bench_startup, implementation, ["startup"])

if __name__ == "__main__":
    director.cli()
