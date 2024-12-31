import abc
import datetime
from pathlib import Path
from typing import Protocol, TypedDict


class BenchAccessProto(Protocol):
    @abc.abstractmethod
    def get_name_and_subname(self) -> tuple[str, str]:
        raise NotImplementedError

    @abc.abstractmethod
    def bench_result_file(self, bench_id: str) -> Path:
        raise NotImplementedError

    @abc.abstractmethod
    def env_spec_str(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_id(self, schema) -> str:
         raise NotImplementedError



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
    def __init__(self, accessor: BenchAccessProto):
        return

    @abc.abstractmethod
    def write_bench_data(self, record: BenchRecord) -> None:
        return


class BenchReader(Protocol):

    @abc.abstractmethod
    def read_bench_data(self, bench_id: str) -> bytes:
        raise NotImplementedError
