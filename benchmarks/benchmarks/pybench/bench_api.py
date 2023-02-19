from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass
class BenchmarkPlan:
    func: Callable[..., Any]
    args: Iterable[Any]


def benchmark_plan(func: Callable[..., Any], *args) -> BenchmarkPlan:
    return BenchmarkPlan(func, args)
