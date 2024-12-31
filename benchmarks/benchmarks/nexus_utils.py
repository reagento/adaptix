import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence, Union

import pyperf


@dataclass
class BenchmarkMeasure:
    base: str
    tags: Sequence[str]
    kwargs: Mapping[str, Any]
    distributions: Mapping[str, str]
    pyperf: pyperf.Benchmark


def pyperf_bench_to_measure(data: Union[str, bytes]) -> BenchmarkMeasure:
    pybench_data = json.loads(data)["pybench_data"]
    return BenchmarkMeasure(
        base=pybench_data["base"],
        tags=pybench_data["tags"],
        kwargs=pybench_data["kwargs"],
        distributions=pybench_data["distributions"],
        pyperf=pyperf.Benchmark.loads(data),
    )


@dataclass(frozen=True)
class EnvDescription:
    key: str
    title: str
    tox_env: str


BENCHMARK_ENVS: Iterable[EnvDescription] = [
    EnvDescription(
        title="CPython 3.8",
        key="py38",
        tox_env="py38-bench",
    ),
    EnvDescription(
        title="CPython 3.9",
        key="py39",
        tox_env="py39-bench",
    ),
    EnvDescription(
        title="CPython 3.10",
        key="py310",
        tox_env="py310-bench",
    ),
    EnvDescription(
        title="CPython 3.11",
        key="py311",
        tox_env="py311-bench",
    ),
    EnvDescription(
        title="CPython 3.12",
        key="py312",
        tox_env="py312-bench",
    ),
    EnvDescription(
        title="PyPy 3.8",
        key="pypy38",
        tox_env="pypy38-bench",
    ),
    EnvDescription(
        title="PyPy 3.9",
        key="pypy39",
        tox_env="pypy39-bench",
    ),
    EnvDescription(
        title="PyPy 3.10",
        key="pypy310",
        tox_env="pypy310-bench",
    ),
]
KEY_TO_ENV = {
    env_description.key: env_description
    for env_description in BENCHMARK_ENVS
}
