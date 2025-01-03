import abc
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence, TypedDict


@dataclass(frozen=True)
class BenchMeta:
    benchmark_name: str
    benchmark_subname: str


class BenchSchemaProto(Protocol):
    tags: Sequence[str]
    base: str


class BenchAccessProto(Protocol):
    meta: BenchMeta
    schemas: Sequence[BenchSchemaProto]

    @abc.abstractmethod
    def bench_result_file(self, bench_id: str) -> Path:
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
    def write_bench_data(self, record: BenchRecord) -> None:
        return


class BenchReader(Protocol):

    @abc.abstractmethod
    def read_schemas_content(self) -> Sequence[str]:
        raise NotImplementedError


class BenchOperator(BenchReader, BenchWriter, Protocol):
    pass
