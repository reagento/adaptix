from benchmarks import bench_backend_types
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams

director = BenchmarkDirector(
    benchmark="backend_types",
    env_spec=benchmark_env_spec(),
    check_params=lambda env_spec: CheckParams(stdev_rel_threshold=0.04),
)

bench_backend_types.expand_scalar_unions()

for operation, entry_point in (
    ("loading", bench_backend_types.bench_loading),
    ("dumping", bench_backend_types.bench_dumping),
):
    for workload in bench_backend_types.WORKLOADS:
        if not bench_backend_types.supports_comparison(workload, operation):
            continue
        for implementation in bench_backend_types.IMPLEMENTATIONS:
            director.add(
                BenchSchema(
                    entry_point=entry_point,
                    base=implementation,
                    tags=[operation, workload],
                    kwargs={"implementation": implementation, "workload": workload},
                    used_distributions=["adaptix", "msgspec"] if implementation == "adaptix_x86_64" else ["msgspec"],
                    skip_if=skip_native if implementation == "adaptix_x86_64" else None,
                ),
            )

if __name__ == "__main__":
    director.cli()
