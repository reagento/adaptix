import contextlib
import datetime
from collections.abc import Iterator
from typing import TypedDict

import pysqlite3 as sqlite3

DATABASE_FILE_NAME = "adaptix_bench.db"


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
    with sqlite3.connect(database_name) as con:
        cursor = con.cursor()
        cursor.execute(create_table_ddl_q)
        cursor.execute(unique_index_ddl_q)
        con.commit()
        cursor.close()


def write_bench(bench_data: BenchRecord, cursor: sqlite3.Cursor):
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
    cursor.execute(insert_q, (
        bench_data["is_actual"], bench_data["benchmark_name"],
        bench_data["benchmark_subname"], bench_data["base"],
        bench_data["local_id"], bench_data["global_id"],
        bench_data["tags"], bench_data["kwargs"], bench_data["distributions"],
        bench_data["data"], bench_data["created_at"],
    ))

@contextlib.contextmanager
def database_manager(db_name: str) -> Iterator[sqlite3.Cursor]:
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


if __name__ == "__main__":
    migrate_sqlite(DATABASE_FILE_NAME)
