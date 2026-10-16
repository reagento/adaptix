from adaptix import CodeGenBackend, DebugTrail
from benchmarks.gh_issues import (
    bench_adaptix,
    bench_cattrs,
    bench_dataclass_factory,
    bench_marshmallow,
    bench_mashumaro,
    bench_pydantic,
    bench_schematics,
)
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams

director = BenchmarkDirector(
    benchmark="gh_issues/loading",
    env_spec=benchmark_env_spec(),
    check_params=lambda env_spec: CheckParams(
        stdev_rel_threshold=0.07 if env_spec["py_impl"] == "pypy" else 0.04,
    ),
)

for backend in CodeGenBackend:
    for strict_coercion in (True, False):
        for debug_trail in DebugTrail:
            director.add(
                BenchSchema(
                    entry_point=bench_adaptix.bench_loading,
                    base="adaptix",
                    tags=[backend.value, *(["sc"] if strict_coercion else []), f"dt_{debug_trail.value.lower()}"],
                    kwargs={
                        "strict_coercion": strict_coercion,
                        "debug_trail": debug_trail.value,
                        "codegen_backend": backend.value,
                    },
                    used_distributions=["adaptix"],
                    skip_if=skip_native if backend == CodeGenBackend.X86_64 else None,
                ),
            )

director.add(
    BenchSchema(
        entry_point=bench_mashumaro.bench_loading,
        base="mashumaro",
        tags=[],
        kwargs={"lazy_compilation": False},
        used_distributions=["mashumaro"],
    ),
    BenchSchema(
        entry_point=bench_mashumaro.bench_loading,
        base="mashumaro",
        tags=["lc"],
        kwargs={"lazy_compilation": True},
        used_distributions=["mashumaro"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_pydantic.bench_loading,
        base="pydantic",
        tags=[],
        kwargs={},
        used_distributions=["pydantic"],
        check_params=lambda env_spec: CheckParams(
            stdev_rel_threshold=0.3 if env_spec["py_impl"] == "pypy" else None,
            ignore_pyperf_warnings=True if env_spec["py_impl"] == "pypy" else None,
        ),
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_cattrs.bench_loading,
        base="cattrs",
        tags=["dv"],
        kwargs={"detailed_validation": True},
        used_distributions=["cattrs"],
    ),
    BenchSchema(
        entry_point=bench_cattrs.bench_loading,
        base="cattrs",
        tags=[],
        kwargs={"detailed_validation": False},
        used_distributions=["cattrs"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_schematics.bench_loading,
        base="schematics",
        tags=[],
        kwargs={},
        used_distributions=["schematics"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_dataclass_factory.bench_loading,
        base="dataclass_factory",
        tags=["dp"],
        kwargs={"debug_path": True},
        used_distributions=["dataclass_factory"],
        skip_if=lambda env_spec: tuple(map(int, env_spec["py"].split(".")[:2])) >= (3, 14),
    ),
    BenchSchema(
        entry_point=bench_dataclass_factory.bench_loading,
        base="dataclass_factory",
        tags=[],
        kwargs={"debug_path": False},
        used_distributions=["dataclass_factory"],
        skip_if=lambda env_spec: tuple(map(int, env_spec["py"].split(".")[:2])) >= (3, 14),
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_marshmallow.bench_loading,
        base="marshmallow",
        tags=[],
        kwargs={},
        used_distributions=["marshmallow"],
    ),
)

director.add(
    BenchSchema(
        entry_point="benchmarks.gh_issues.bench_msgspec:bench_loading",
        base="msgspec",
        tags=[],
        kwargs={"strict": False, "no_gc": False},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
    BenchSchema(
        entry_point="benchmarks.gh_issues.bench_msgspec:bench_loading",
        base="msgspec",
        tags=["strict"],
        kwargs={"strict": True, "no_gc": False},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
    BenchSchema(
        entry_point="benchmarks.gh_issues.bench_msgspec:bench_loading",
        base="msgspec",
        tags=["no_gc"],
        kwargs={"strict": False, "no_gc": True},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
    BenchSchema(
        entry_point="benchmarks.gh_issues.bench_msgspec:bench_loading",
        base="msgspec",
        tags=["strict", "no_gc"],
        kwargs={"strict": True, "no_gc": True},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
)

if __name__ == "__main__":
    director.cli()
