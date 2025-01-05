from itertools import chain
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from benchmarks.pybench.persistence.common import BenchAccessProto, BenchOperator, BenchRecord


class FileSystemBenchOperator(BenchOperator):

    def __init__(self, accessor: BenchAccessProto):
        self.accessor = accessor

    def write_bench_data(self, record: BenchRecord) -> None:
        result_file = self.accessor.bench_result_file(record["global_id"])
        result_file.write_bytes(record["data"])

    def read_benchmarks_results(self):
        content_container = []
        for schema in self.accessor.schemas:
            path = self.accessor.bench_result_file(self.accessor.get_id(schema))
            content_container.append(
                path.read_text(),
            )
        return content_container

    def bench_data(self, schema: Any) -> str | None:
        try:
            return self.accessor.bench_result_file(self.accessor.get_id(schema)).read_text()
        except FileNotFoundError:
            return None

    def write_release_files(
        self,
        release_zip: ZipFile,
        files: list[Path],
    ) -> None:
        for file_path in files:
            release_zip.write(file_path, arcname=file_path.name)


def filesystem_operator_factory(accessor: BenchAccessProto) -> FileSystemBenchOperator:
    return FileSystemBenchOperator(accessor)
