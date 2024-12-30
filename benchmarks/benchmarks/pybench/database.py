import contextlib
from typing import Iterator

import pysqlite3 as sqlite3

from benchmarks.pybench.common import BenchRecord, BenchWriter

DATABASE_FILE_NAME = "adaptix_bench.db"





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

class SQLite3BenchWriter(BenchWriter):
    def __init__(self, db_name: str):
        self.db_name = db_name

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


def sqlite3_writer() -> SQLite3BenchWriter:
    return SQLite3BenchWriter(DATABASE_FILE_NAME)


if __name__ == "__main__":
    migrate_sqlite(DATABASE_FILE_NAME)
