from benchmarks import bench_json_codegen
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams
from benchmarks.simple_structures.hub_codegen import director as codegen_director, skip_native

director = BenchmarkDirector(
    benchmark="json_codegen",
    env_spec=codegen_director.env_spec,
    check_params=lambda env_spec: CheckParams(stdev_rel_threshold=0.04),
)

for workload in bench_json_codegen.WORKLOADS:
    for operation in bench_json_codegen.OPERATIONS:
        for data_format in bench_json_codegen.FORMATS:
            for implementation in bench_json_codegen.IMPLEMENTATIONS:
                director.add(
                    BenchSchema(
                        entry_point=bench_json_codegen.bench_json,
                        base=implementation,
                        tags=[operation, workload, data_format],
                        kwargs={
                            "implementation": implementation,
                            "workload": workload,
                            "operation": operation,
                            "data_format": data_format,
                        },
                        used_distributions=["msgspec"] if implementation == "msgspec" else ["adaptix"],
                        skip_if=skip_native
                        if implementation in {"adaptix_native_json", "adaptix_stdlib_json"}
                        else None,
                    ),
                )

if __name__ == "__main__":
    director.cli()
