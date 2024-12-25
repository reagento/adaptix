import datetime
import sqlite3
from typing import TypedDict


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
        cursor.close()

