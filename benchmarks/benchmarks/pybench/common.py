import abc
import datetime
from typing import Protocol, TypedDict


class BenchRecord(TypedDict):
    is_actual: bool
    benchmark_name: str
    benchmark_subname: str
    base: str
    local_id: str
    global_id: str
    tags: str
    kwargs: str
    distributions: str
    data: bytes
    created_at: datetime.datetime

class BenchWriter(Protocol):

    @abc.abstractmethod
    def write_bench_data(self, record: BenchRecord) -> None:
        return


class BenchReader(Protocol):

    @abc.abstractmethod
    def read_bench_data(self, bench_id: ...) -> ...:
        ...
