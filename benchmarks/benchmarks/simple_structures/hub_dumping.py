from adaptix import CodeGenBackend, DebugTrail
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams
from benchmarks.simple_structures import (
    bench_adaptix,
    bench_asdict,
    bench_cattrs,
    bench_dataclass_factory,
    bench_marshmallow,
    bench_mashumaro,
    bench_pydantic,
    bench_schematics,
)

REVIEWS_COUNT = 100

director = BenchmarkDirector(
    benchmark="simple_structures/dumping",
    env_spec=benchmark_env_spec(),
    check_params=lambda env_spec: CheckParams(
        stdev_rel_threshold=0.07 if env_spec["py_impl"] == "pypy" else 0.04,
    ),
)

for backend in CodeGenBackend:
    for debug_trail in DebugTrail:
        director.add(
            BenchSchema(
                entry_point=bench_adaptix.bench_dumping,
                base="adaptix",
                tags=[backend.value, f"dt_{debug_trail.value.lower()}"],
                kwargs={
                    "reviews_count": REVIEWS_COUNT,
                    "debug_trail": debug_trail.value,
                    "codegen_backend": backend.value,
                },
                used_distributions=["adaptix"],
                skip_if=skip_native if backend == CodeGenBackend.X86_64 else None,
            ),
        )

director.add(
    BenchSchema(
        entry_point=bench_mashumaro.bench_dumping,
        base="mashumaro",
        tags=[],
        kwargs={"lazy_compilation": False, "reviews_count": REVIEWS_COUNT},
        used_distributions=["mashumaro"],
    ),
    BenchSchema(
        entry_point=bench_mashumaro.bench_dumping,
        base="mashumaro",
        tags=["lc"],
        kwargs={"lazy_compilation": True, "reviews_count": REVIEWS_COUNT},
        used_distributions=["mashumaro"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_pydantic.bench_dumping,
        base="pydantic",
        tags=["strict"],
        kwargs={"strict": True, "reviews_count": REVIEWS_COUNT},
        used_distributions=["pydantic"],
        check_params=lambda env_spec: CheckParams(
            stdev_rel_threshold=0.15 if env_spec["py_impl"] == "pypy" else None,
            ignore_pyperf_warnings=True if env_spec["py_impl"] == "pypy" else None,
        ),
    ),
    BenchSchema(
        entry_point=bench_pydantic.bench_dumping,
        base="pydantic",
        tags=[],
        kwargs={"strict": False, "reviews_count": REVIEWS_COUNT},
        used_distributions=["pydantic"],
        check_params=lambda env_spec: CheckParams(
            stdev_rel_threshold=0.15 if env_spec["py_impl"] == "pypy" else None,
            ignore_pyperf_warnings=True if env_spec["py_impl"] == "pypy" else None,
        ),
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_asdict.bench_dumping,
        base="asdict",
        tags=[],
        kwargs={"reviews_count": REVIEWS_COUNT},
        used_distributions=[],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_cattrs.bench_dumping,
        base="cattrs",
        tags=["dv"],
        kwargs={"detailed_validation": True, "reviews_count": REVIEWS_COUNT},
        used_distributions=["cattrs"],
    ),
    BenchSchema(
        entry_point=bench_cattrs.bench_dumping,
        base="cattrs",
        tags=[],
        kwargs={"detailed_validation": False, "reviews_count": REVIEWS_COUNT},
        used_distributions=["cattrs"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_schematics.bench_dumping,
        base="schematics",
        tags=[],
        kwargs={"reviews_count": REVIEWS_COUNT},
        used_distributions=["schematics"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_dataclass_factory.bench_dumping,
        base="dataclass_factory",
        tags=[],
        kwargs={"reviews_count": REVIEWS_COUNT},
        used_distributions=["dataclass_factory"],
    ),
)

director.add(
    BenchSchema(
        entry_point=bench_marshmallow.bench_dumping,
        base="marshmallow",
        tags=[],
        kwargs={"reviews_count": REVIEWS_COUNT},
        used_distributions=["marshmallow"],
    ),
)

director.add(
    BenchSchema(
        entry_point="benchmarks.simple_structures.bench_msgspec:bench_dumping",
        base="msgspec",
        tags=[],
        kwargs={"no_gc": False, "reviews_count": REVIEWS_COUNT},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
    BenchSchema(
        entry_point="benchmarks.simple_structures.bench_msgspec:bench_dumping",
        base="msgspec",
        tags=["no_gc"],
        kwargs={"no_gc": True, "reviews_count": REVIEWS_COUNT},
        skip_if=lambda env_spec: env_spec["py_impl"] == "pypy",
        used_distributions=["msgspec"],
    ),
)

if __name__ == "__main__":
    director.cli()
