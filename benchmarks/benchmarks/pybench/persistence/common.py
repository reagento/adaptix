import abc
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence, TypedDict
from zipfile import ZipFile


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

    @abc.abstractmethod
    def write_release_files(
        self,
        release_zip: ZipFile,
        files: list[Path],
    ) -> None:
        return


class BenchReader(Protocol):

    @abc.abstractmethod
    def read_benchmarks_results(self) -> Sequence[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def bench_data(self, schema: Any) -> str | None:
        return


class BenchOperator(BenchReader, BenchWriter, Protocol):
    pass
