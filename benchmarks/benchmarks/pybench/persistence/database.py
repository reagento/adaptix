import datetime
import json
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

import pyperf
import pysqlite3 as sqlite3
from sqlalchemy import Sequence

from benchmarks.nexus_utils import KEY_TO_ENV, pyperf_bench_to_measure
from benchmarks.pybench.persistence.common import BenchAccessProto, BenchOperator, BenchRecord

DATABASE_FILE_NAME = "adaptix_bench.db"


class RecordNotFound(Exception):
    def __init__(self, gid: str, name: str, sub_name: str):
        self.gid = gid
        self.name = name
        self.sub_name = sub_name


    def __str__(self):
        return f"""Record not found for {self.name}/{self.sub_name}({self.gid})."""


class IndexNotFound(Exception):
    def __init__(self, hub_key: str):
        self.hub_key = hub_key

    def __str__(self):
        return f"""Index not found - {self.hub_key}"""

def migrate_sqlite(database_name: str):
    create_table_ddl_q = """CREATE TABLE IF NOT EXISTS bench (
    is_actual BOOLEAN,
    benchmark_name TEXT,
    benchmark_subname TEXT,
    base TEXT,
    local_id TEXT,
    global_id TEXT,
    tags TEXT,
    kwargs TEXT,
    distributions TEXT,
    data TEXT,
    created_at DATETIME
    );"""
    unique_index_ddl_q = """CREATE UNIQUE INDEX IF NOT EXISTS bench_unique ON
     bench(benchmark_name, benchmark_subname, global_id) WHERE is_actual=TRUE;"""
    benches_index_ddl_q = """CREATE TABLE IF NOT EXISTS bench_index (
    created_at DATETIME,
    data TEXT,
    hub_key TEXT
    );"""
    with sqlite3.connect(database_name) as con:
        cursor = con.cursor()
        cursor.execute(create_table_ddl_q)
        cursor.execute(unique_index_ddl_q)
        cursor.execute(benches_index_ddl_q)
        con.commit()
        cursor.close()

class SQLite3BenchOperator(BenchOperator):


    GET_BENCH_DATA_Q = """SELECT data, max(created_at) FROM bench WHERE benchmark_name = ?
            AND benchmark_subname = ? and global_id = ?;"""
    GET_INDEX_Q = """SELECT data, max(created_at) FROM bench_index WHERE hub_key = ?;"""


    def __init__(self, accessor: BenchAccessProto | None):
        self.accessor = accessor
        self.db_name = DATABASE_FILE_NAME

    def fill_validation(self, dist_to_versions: defaultdict[..., set]):
        with sqlite3.connect(self.db_name) as con:
            for schema in self.accessor.schemas:
                name, sub_name = self.accessor.get_name_and_subname()
                gid = self.accessor.get_id(schema)
                bench_report = json.loads(
                    self._bench_data(con, gid, name, sub_name),
                )
                for dist, version in bench_report["pybench_data"]["distributions"].items():
                    dist_to_versions[dist].add(version)


    def read_schemas_content(self) -> Sequence[str]:
        assert self.accessor
        con = sqlite3.connect(self.db_name)
        content_container = []
        for schema in self.accessor.schemas:
            global_id = self.accessor.get_id(schema)
            name, sub_name = self.accessor.get_name_and_subname()
            content_container.append(self._bench_data(con, global_id, name, sub_name))
        con.close()
        return content_container

    def _bench_data(self,connection: sqlite3.Connection, bench_id, bench_name: str, bench_sub_name: str) -> bytes:
        result = connection.execute(self.GET_BENCH_DATA_Q, (bench_name, bench_sub_name, bench_id))
        data = result.fetchone()
        if not data:
            raise RecordNotFound(bench_id, bench_name, bench_sub_name)
        return data[0]

    def write_bench_data(self, record: BenchRecord) -> None:
        insert_q = """INSERT OR REPLACE INTO bench (
    is_actual,
    benchmark_name,
    benchmark_subname,
    base,
    local_id,
    global_id,
    tags,
    kwargs,
    distributions,
    data,
    created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?);"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(insert_q, (
                record["is_actual"], record["benchmark_name"],
                record["benchmark_subname"], record["base"],
                record["local_id"], record["global_id"],
                record["tags"], record["kwargs"], record["distributions"],
                record["data"], record["created_at"],
            ))
            conn.commit()

    def get_distributions(self, benchmark_hub: Iterable) -> dict[str, str]:
        distributions: dict[str, str] = {}

        connection = sqlite3.connect(self.db_name)

        for hub_description in benchmark_hub:
            index_result = connection.execute(self.GET_INDEX_Q, (hub_description.key,))
            data = index_result.fetchone()
            if not data:
                raise IndexNotFound(hub_description.key)
            index = json.loads(data[0])
            for index_with_names_list in index["env_ids"].values():
                for gid, name, sub_name in index_with_names_list:
                    bench_data = self._bench_data(connection, gid, name, sub_name)
                    distributions.update(
                        pyperf_bench_to_measure(bench_data).distributions,
                    )
        connection.close()
        return distributions

    def write_release(self, hub_to_director_to_env: Mapping[..., Mapping]) -> None:
        write_release_q = """INSERT INTO bench_index(created_at, data, hub_key) VALUES(?, ?, ?);"""
        con = sqlite3.connect(self.db_name)
        current_dt = datetime.datetime.now(tz=datetime.timezone.utc)
        for hub_description, env_to_director in hub_to_director_to_env.items():
            env_with_accessor = [
                (env_description, director.make_accessor())
                for env_description, director in env_to_director.items()
            ]
            env_to_global_ids = {
                env_description: [
                    [accessor.get_id(schema), *accessor.get_name_and_subname()]
                    for schema in accessor.schemas
                ]
                for env_description, accessor in env_with_accessor
            }
            con.execute(write_release_q, (current_dt, json.dumps(
                        self.get_index(env_to_global_ids)), hub_description.key))
        con.commit()
        con.close()

    def get_index(self, mapped_data: Mapping) -> dict[str, Any]:
        return {"env_ids": {
            env_description.key: list(ids_with_names),
        } for env_description, ids_with_names in mapped_data.items()}

    def release_to_measures(self, hub_key: str) -> Mapping[..., Sequence]:
        con = sqlite3.connect(self.db_name)
        result = con.execute(self.GET_INDEX_Q, (hub_key,))
        data = result.fetchone()
        if not data:
            raise IndexNotFound(hub_key)
        index = json.loads(data[0])
        env_to_ids = {
            KEY_TO_ENV[env_key]: ids_and_names
            for env_key, ids_and_names in index["env_ids"].items()
        }
        env_to_measures: dict[..., Sequence] = {}
        for env, ids in env_to_ids:
            benches = []
            for gid, name, sub_name in ids:
                benches.append(self._bench_data(con, gid, name, sub_name))
            env_to_measures[env] = sorted((pyperf_bench_to_measure(bench) for bench in benches), key=lambda x: x.pyperf.mean())
        return env_to_measures

    def load_benchmarks(self) -> Sequence:
        loaded = []
        with TemporaryDirectory() as temp_dir, sqlite3.connect(self.db_name) as con:
            for schema in self.accessor.schemas:
                name, sub_name = self.accessor.get_name_and_subname()
                gid = self.accessor.get_id(schema)
                bench_data = self._bench_data(con, gid, name, sub_name)
                fp = Path(temp_dir) / f"{gid}.json"
                fp.write_bytes(bench_data)
                loaded.append(pyperf.Benchmark.load(str(fp)))
        return loaded


if __name__ == "__main__":
    migrate_sqlite(DATABASE_FILE_NAME)
