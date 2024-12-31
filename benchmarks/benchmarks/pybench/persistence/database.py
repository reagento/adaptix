import pysqlite3 as sqlite3

from benchmarks.pybench.persistence.common import BenchAccessProto, BenchReader, BenchRecord, BenchWriter

DATABASE_FILE_NAME = "adaptix_bench.db"


class RecordNotFound(Exception):
    def __init__(self, gid: str, name: str, sub_name: str):
        self.gid = gid
        self.name = name
        self.sub_name = sub_name

    def __str__(self):
        return f"""Record not found for {self.name}/{self.sub_name}({self.gid})."""

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
    data TEXT
    );"""
    with sqlite3.connect(database_name) as con:
        cursor = con.cursor()
        cursor.execute(create_table_ddl_q)
        cursor.execute(unique_index_ddl_q)
        cursor.execute(benches_index_ddl_q)
        con.commit()
        cursor.close()

class SQLite3BenchOperator(BenchWriter, BenchReader):
    def read_bench_data(self, bench_id: str) -> bytes:
        get_bench_data_q = """SELECT data FROM bench WHERE benchmark_name = ?
        AND benchmark_subname = ? and global_id = ?;"""
        con =  sqlite3.connect(self.db_name)
        result = con.execute(get_bench_data_q, (*self.accessor.get_name_and_subname(), bench_id))
        data = result.fetchone()
        if data:
            return data[0]
        raise RecordNotFound(bench_id, *self.accessor.get_name_and_subname())

    def __init__(self, accessor: BenchAccessProto):
        self.accessor = accessor
        self.db_name = DATABASE_FILE_NAME

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


if __name__ == "__main__":
    migrate_sqlite(DATABASE_FILE_NAME)
