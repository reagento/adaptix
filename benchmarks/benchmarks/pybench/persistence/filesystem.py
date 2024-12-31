import json
from collections import defaultdict
from itertools import chain
from typing import Any, Iterable, Mapping, Sequence
from zipfile import ZIP_BZIP2, ZipFile

import pyperf

from benchmarks.bench_nexus import RELEASE_DATA, HubDescription
from benchmarks.nexus_utils import KEY_TO_ENV, BenchmarkMeasure, EnvDescription, pyperf_bench_to_measure
from benchmarks.pybench.director_api import BenchmarkDirector
from benchmarks.pybench.persistence.common import BenchAccessProto, BenchOperator, BenchRecord


class FileSystemBenchOperator(BenchOperator):

    def __init__(self, accessor: BenchAccessProto | None):
        self.accessor = accessor

    def fill_validation(self, dist_to_versions: defaultdict[..., set]):
        for schema in self.accessor.schemas:
            bench_report = json.loads(
                self.accessor.bench_result_file(self.accessor.get_id(schema)).read_text(),
            )
            for dist, version in bench_report["pybench_data"]["distributions"].items():
                dist_to_versions[dist].add(version)

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

    def write_release(self, hub_to_director_to_env: Mapping[HubDescription, Mapping[EnvDescription, BenchmarkDirector]]) -> None:
        for hub_description, env_to_director in hub_to_director_to_env.items():
            env_with_accessor = [
                (env_description, director.make_accessor())
                for env_description, director in env_to_director.items()
            ]
            env_to_files = {
                env_description: [
                    accessor.bench_result_file(accessor.get_id(schema))
                    for schema in accessor.schemas
                ]
                for env_description, accessor in env_with_accessor
            }
            with ZipFile(
                file=RELEASE_DATA / f"{hub_description.key}.zip",
                mode="w",
                compression=ZIP_BZIP2,
                compresslevel=9,
            ) as release_zip:
                for file_path in chain.from_iterable(env_to_files.values()):
                    release_zip.write(file_path, arcname=file_path.name)

                release_zip.writestr(
                    "index.json",
                    json.dumps(
                        self.get_index(env_to_files),
                    ),
                )

    def get_distributions(self, benchmark_hub: Iterable) -> dict[str, str]:

        distributions: dict[str, str] = {}

        for hub_description in benchmark_hub:
            with ZipFile(RELEASE_DATA / f"{hub_description.key}.zip") as release_zip:
                index = json.loads(release_zip.read("index.json"))
                for file_list in index["env_files"].values():
                    for file in file_list:
                        distributions.update(
                            pyperf_bench_to_measure(release_zip.read(file)).distributions,
                        )
        return distributions

    def get_index(self, mapped_data: Mapping) -> dict[str, Any]:
        return {
            "env_files": {
                env_description.key: [
                    file.name for file in files
                ]
                for env_description, files in mapped_data.items()
            },
        }

    def release_to_measures(self, hub_key: str) -> Mapping[EnvDescription, Sequence[BenchmarkMeasure]]:
        with ZipFile(RELEASE_DATA / f"{hub_key}.zip") as release_zip:
            index = json.loads(release_zip.read("index.json"))
            env_to_files = {
                KEY_TO_ENV[env_key]: files
                for env_key, files in index["env_files"].items()
            }
            return {
                env: sorted(
                    (
                        pyperf_bench_to_measure(release_zip.read(file))
                        for file in files
                    ),
                    key=lambda x: x.pyperf.mean(),
                )
                for env, files in env_to_files.items()
            }

    def load_benchmarks(self) -> Sequence:
        return [
            pyperf.Benchmark.load(
                str(self.accessor.bench_result_file(self.accessor.get_id(schema))),
            )
            for schema in self.accessor.schemas
        ]
