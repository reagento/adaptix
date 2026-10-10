from dataclasses import replace

from benchmarks.pybench.director_api import BenchmarkDirector, CheckParams
from benchmarks.simple_structures.hub_codegen import director as codegen_director
from benchmarks.simple_structures.hub_dumping import director as dumping_director
from benchmarks.simple_structures.hub_loading import director as loading_director

director = BenchmarkDirector(
    benchmark="simple_structures/competitors",
    env_spec=codegen_director.env_spec,
    check_params=lambda env_spec: CheckParams(
        stdev_rel_threshold=0.07 if env_spec["py_impl"] == "pypy" else 0.04,
    ),
)

# Keep the same Book with 100 reviews, aliases, and benchmark functions as the
# existing hubs. Separate tags preserve the validation and GC settings.
director.add_iter(
    schema
    for schema in codegen_director.schemas
    if schema.kwargs["workload"] == "nested"
)
director.add_iter(
    replace(schema, tags=["loading", *schema.tags])
    for schema in loading_director.schemas
    if schema.base != "adaptix" and not (schema.base == "mashumaro" and "lc" in schema.tags)
)
director.add_iter(
    replace(schema, tags=["dumping", *schema.tags])
    for schema in dumping_director.schemas
    if schema.base not in {"adaptix", "asdict"}
    and not (schema.base == "mashumaro" and "lc" in schema.tags)
    and not (schema.base == "pydantic" and "strict" not in schema.tags)
    and not (schema.base == "cattrs" and "dv" not in schema.tags)
)

if __name__ == "__main__":
    director.cli()
