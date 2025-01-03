from benchmarks.pybench.persistence.common import BenchAccessProto, BenchOperator, BenchRecord


class FileSystemBenchOperator(BenchOperator):

    def __init__(self, accessor: BenchAccessProto | None):
        self.accessor = accessor

    def write_bench_data(self, record: BenchRecord) -> None:
        result_file = self.accessor.bench_result_file(record["global_id"])
        result_file.write_bytes(record["data"])

    def read_schemas_content(self):
        content_container = []
        for schema in self.accessor.schemas:
            path = self.accessor.bench_result_file(self.accessor.get_id(schema))
            content_container.append(
                path.read_text(),
            )
        return content_container


def filesystem_operator_factory(accessor: BenchAccessProto | None = None) -> FileSystemBenchOperator:
    return FileSystemBenchOperator(accessor)
