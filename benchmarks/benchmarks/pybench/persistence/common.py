import abc
import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence, TypedDict

from mypy.memprofile import defaultdict


class BenchSchemaProto(Protocol):
    tags: Sequence[str]
    base: str

class BenchAccessProto(Protocol):

    schemas: Sequence[BenchSchemaProto]

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
    def write_bench_data(self, record: BenchRecord) -> None:
        return

    @abc.abstractmethod
    def write_release(self, hub_to_director_to_env: Mapping[..., Mapping]) -> None:
        return


class BenchReader(Protocol):

    @abc.abstractmethod
    def read_schemas_content(self) -> Sequence[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def release_to_measures(self, hub_key: str) -> Mapping[..., Sequence[...]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_distributions(self, benchmark_hub: Iterable) -> dict[str, str]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_benchmarks(self) -> Sequence:
        raise NotImplementedError

    @abc.abstractmethod
    def fill_validation(self, dist_to_versions: defaultdict[..., set]):
        return


class BenchOperator(BenchReader, BenchWriter, Protocol):

    @abc.abstractmethod
    def __init__(self, accessor: BenchAccessProto | None):
        return

    @abc.abstractmethod
    def get_index(self, mapped_data: Mapping) -> dict[str, Any]:
        raise NotImplementedError
