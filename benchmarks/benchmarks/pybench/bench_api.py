from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkPlan:
    func: Callable[..., Any]
    args: Iterable[Any]


def benchmark_plan(func: Callable[..., Any], *args) -> BenchmarkPlan:
    return BenchmarkPlan(func, args)
