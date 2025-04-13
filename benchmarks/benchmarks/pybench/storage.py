import json
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TypedDict

from pyperf._formatter import format_timedelta


class PybenchData(TypedDict):
    case_id: str
    base: str
    tags: Iterable[str]
    env_spec: Mapping[str, str]
    kwargs: Mapping[str, Any]
    distributions: Mapping[str, str]


class BenchCaseResult(TypedDict):
    pybench_data: PybenchData


class BenchCaseResultStats(TypedDict):
    mean: float
    stdev: float
    rel_stdev: float


class BenchStorage(ABC):
    @abstractmethod
    def write_case_result(self, result: BenchCaseResult, stats: BenchCaseResultStats) -> None:
        ...

    @abstractmethod
    def get_case_result(self, case_id: str) -> Optional[BenchCaseResult]:
        ...


class UninitedBenchStorage(BenchStorage):
    def write_case_result(self, result: BenchCaseResult, stats: BenchCaseResultStats) -> None:
        raise NotImplementedError

    def get_case_result(self, case_id: str) -> Optional[BenchCaseResult]:
        raise NotImplementedError


class FilesystemBenchStorage(BenchStorage):
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def _get_result_file(self, case_id: str) -> Path:
        return self._data_dir / f"{case_id}.json"

    def write_case_result(self, result: BenchCaseResult, stats: BenchCaseResultStats) -> None:
        result_file = self._get_result_file(result["pybench_data"]["case_id"])
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text(json.dumps(result))

    def get_case_result(self, case_id: str) -> Optional[BenchCaseResult]:
        try:
            result_text = self._get_result_file(case_id).read_text()
        except FileNotFoundError:
            return None
        return json.loads(result_text)


class SqliteBenchStorage(BenchStorage):
    INIT_DB_QUERY = """
        CREATE TABLE IF NOT EXISTS benches (
            benchmark TEXT,
            case_id TEXT,
            is_actual BOOLEAN,

            mean TEXT,
            stdev TEXT,
            rel_stdev TEXT,

            base TEXT,
            tags JSON,
            env_spec JSON,

            kwargs JSON,
            distributions JSON,
            result JSON,
            stats JSON,

            created_at DATETIME
        );
        CREATE UNIQUE INDEX IF NOT EXISTS benches_unique ON benches (
            benchmark, case_id
        ) WHERE is_actual=TRUE;
    """

    DEACTUALIZE_RECORD_QUERY = """
        UPDATE benches SET is_actual=FALSE WHERE (
            benchmark=:benchmark AND case_id=:case_id AND is_actual=TRUE
        );
    """
    INSERT_BENCH_RECORD_QUERY = """
        INSERT OR REPLACE INTO benches (
            benchmark,
            case_id,
            is_actual,

            mean,
            stdev,
            rel_stdev,

            base,
            tags,
            env_spec,

            kwargs,
            distributions,
            result,
            stats,

            created_at
        ) VALUES (
            :benchmark,
            :case_id,
            TRUE,

            :mean,
            :stdev,
            :rel_stdev,

            :base,
            :tags,
            :env_spec,

            :kwargs,
            :distributions,
            :result,
            :stats,

            :created_at
        );
    """

    GET_BENCH_RESULT_QUERY = """
        SELECT result FROM benches WHERE (
            benchmark=:benchmark AND case_id = :case_id AND is_actual=TRUE
        );
    """

    def __init__(self, db_path: str, benchmark: str):
        self._db_path = db_path
        self._benchmark = benchmark
        self._db_is_inited = False

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        if not self._db_is_inited:
            connection.executescript(self.INIT_DB_QUERY)
            connection.commit()
            self._db_is_inited = True
        return connection

    def _format_time(self, time: float) -> str:
        return format_timedelta(time)

    def _format_relation(self, relation: float) -> str:
        return f"{relation:.1%}"

    def write_case_result(self, result: BenchCaseResult, stats: BenchCaseResultStats) -> None:
        pybench_data = result["pybench_data"]
        with self._connect() as connection:
            connection.execute(
                self.DEACTUALIZE_RECORD_QUERY,
                {
                    "benchmark": self._benchmark,
                    "case_id": pybench_data["case_id"],
                },
            )
            connection.execute(
                self.INSERT_BENCH_RECORD_QUERY,
                {
                    "benchmark": self._benchmark,
                    "case_id": pybench_data["case_id"],
                    "base": pybench_data["base"],
                    "mean": self._format_time(stats["mean"]),
                    "stdev": self._format_time(stats["stdev"]),
                    "rel_stdev": self._format_relation(stats["rel_stdev"]),
                    "tags": json.dumps(pybench_data["tags"]),
                    "env_spec": json.dumps(pybench_data["env_spec"]),
                    "kwargs": json.dumps(pybench_data["kwargs"]),
                    "distributions": json.dumps(pybench_data["distributions"]),
                    "result": json.dumps(result),
                    "stats": json.dumps(stats),
                    "created_at": datetime.now(tz=timezone.utc),
                },
            )
            connection.commit()

    def get_case_result(self, case_id: str) -> Optional[BenchCaseResult]:
        with self._connect() as connection:
            result = connection.execute(
                self.GET_BENCH_RESULT_QUERY,
                {
                    "benchmark": self._benchmark,
                    "case_id": case_id,
                },
            ).fetchone()
        return None if result is None else json.loads(result[0])
