# pylint: disable=import-error,no-name-in-module
# ruff: noqa: T201, S603
import importlib.metadata
import inspect
import json
import os
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Iterable, Mapping, Sequence
from copy import copy
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Literal, Optional, TypeVar, Union

import pyperf
from pyperf._cli import format_checks

from benchmarks.pybench.storage import (
    BenchCaseResult,
    BenchCaseResultStats,
    BenchStorage,
    FilesystemBenchStorage,
    SqliteBenchStorage,
    UninitedBenchStorage,
)
from benchmarks.pybench.utils import get_function_object_ref, load_by_object_ref

__all__ = (
    "BenchAccessor",
    "BenchChecker",
    "BenchSchema",
    "BenchmarkDirector",
    "CheckParams",
)

EnvSpec = Mapping[str, str]


@dataclass(frozen=True)
class CheckParams:
    stdev_rel_threshold: Optional[float] = None
    ignore_pyperf_warnings: Optional[bool] = None


@dataclass(frozen=True)
class BenchSchema:
    entry_point: Union[Callable, str]
    base: str
    tags: Iterable[str]
    kwargs: Mapping[str, Any]
    used_distributions: Sequence[str]
    skip_if: Optional[Callable[[EnvSpec], bool]] = None
    check_params: Callable[[EnvSpec], CheckParams] = lambda env_spec: CheckParams()


BUILTIN_CHECK_PARAMS = CheckParams(
    ignore_pyperf_warnings=False,
)


class BenchStorageFactory:
    def __init__(self, benchmark: str):
        self.benchmark = benchmark

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        parser.add_argument("--storage-type", "-st", choices=["fs", "sqlite"])
        parser.add_argument("--sqlite-db", action="store", required=False, type=Path)
        parser.add_argument("--fs-data-dir", action="store", required=False, type=Path)

    def create(
        self,
        storage_type: Optional[Literal["fs", "sqlite"]] = None,
        sqlite_db: Optional[Path] = None,
        fs_data_dir: Optional[Path] = None,
    ) -> BenchStorage:
        if storage_type is None or storage_type == "sqlite":
            return SqliteBenchStorage(
                db_path=str(
                    Path(__file__).parent.parent.parent / "data" / "bench_results.sqlite"
                    if sqlite_db is None else
                    sqlite_db,
                ),
                benchmark=self.benchmark,
            )
        elif storage_type == "fs":  # noqa: RET505
            return FilesystemBenchStorage(
                data_dir=(
                    Path(__file__).parent.parent.parent / "data" / self.benchmark
                    if fs_data_dir is None else
                    fs_data_dir
                ),
            )
        raise ValueError(f"Bad storage_type {storage_type!r}")


class BenchAccessor:
    def __init__(
        self,
        benchmark: str,
        storage: BenchStorage,
        env_spec: EnvSpec,
        check_params: Callable[[EnvSpec], CheckParams],
        schemas: Sequence[BenchSchema],
    ):
        self.benchmark = benchmark
        self._storage = storage
        self.env_spec = env_spec
        self.all_schemas = schemas
        self.id_to_schema: dict[str, BenchSchema] = {self.get_id(schema): schema for schema in schemas}
        self._base_check_params = check_params

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--env-spec", action="extend", nargs="+", required=False, metavar="KEY=VALUE")

    def override_state(self, env_spec: Optional[Iterable[str]]):
        if env_spec is not None:
            update_data = {}
            for item in env_spec:
                key, value = item.split("=")
                if key not in self.env_spec:
                    raise KeyError(f"Unexpected key {key}")
                update_data[key] = value
            self.env_spec = {**self.env_spec, **update_data}

    def set_storage(self, storage: BenchStorage) -> None:
        self._storage = storage

    def env_spec_str(self) -> str:
        return "[" + "-".join(f"{k}={v}" for k, v in self.env_spec.items()) + "]"

    def get_id(self, schema: BenchSchema) -> str:
        return self.get_local_id(schema) + self.env_spec_str()

    def get_local_id(self, schema: BenchSchema) -> str:
        if schema.tags:
            tags_str = "-" + "-".join(schema.tags)
            return schema.base + tags_str
        return schema.base

    def get_label(self, schema: BenchSchema) -> str:
        if schema.tags:
            tags_str = ", ".join(schema.tags)
            return f"{schema.base}\n({tags_str})"
        return schema.base

    def _chain_check_param(self, base_check_params: CheckParams, key: str, value: Any) -> Any:
        if value is not None:
            return value
        base_value = getattr(base_check_params, key)
        if base_value is not None:
            return base_value
        builtin_value = getattr(BUILTIN_CHECK_PARAMS, key)
        if builtin_value is None:
            raise ValueError(f"Check param {key!r} must be filled")
        return builtin_value

    def resolve_check_params(self, schema: BenchSchema) -> CheckParams:
        base_check_params = self._base_check_params(self.env_spec)
        return CheckParams(
            **{
                key: self._chain_check_param(base_check_params, key, value)
                for key, value in vars(schema.check_params(self.env_spec)).items()
            },
        )

    @cached_property
    def schemas(self) -> Sequence[BenchSchema]:
        return [
            schema
            for schema in self.all_schemas
            if schema.skip_if is None or not schema.skip_if(self.env_spec)
        ]

    def get_case_result(self, schema: BenchSchema) -> Optional[BenchCaseResult]:
        return self._storage.get_case_result(self.get_id(schema))

    def get_existing_case_result(self, schema: BenchSchema) -> BenchCaseResult:
        schema_id = self.get_id(schema)
        case_result = self._storage.get_case_result(schema_id)
        if case_result is None:
            raise KeyError(f"Result for {schema_id!r} of {self.benchmark!r} not found")
        return case_result

    def write_case_result(self, result: BenchCaseResult, stats: BenchCaseResultStats) -> None:
        return self._storage.write_case_result(result, stats)


class BenchChecker:
    def __init__(self, accessor: BenchAccessor):
        self.accessor = accessor

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--local-id-list", action="store_true", required=False, default=False,
            help="print only schema list with errors",
        )

    def _process_pyperf_warnings(
        self,
        schema: BenchSchema,
        bench: pyperf.Benchmark,
        check_params: CheckParams,
        warnings: Iterable[str],
    ) -> Iterable[str]:
        if check_params.ignore_pyperf_warnings:
            return []
        return [
            line
            for line in warnings
            if not line.startswith("Use")
        ]

    def get_warnings(self, schema: BenchSchema) -> Optional[Sequence[str]]:
        data = self.accessor.get_case_result(schema)
        if data is None:
            return None
        bench = pyperf.Benchmark.loads(json.dumps(data))
        check_params = self.accessor.resolve_check_params(schema)
        warnings = self._process_pyperf_warnings(schema, bench, check_params, format_checks(bench))
        self_warnings = self._check_yourself(schema, bench, check_params)
        return [*warnings, *self_warnings]

    def _check_yourself(self, schema: BenchSchema, bench: pyperf.Benchmark, check_params: CheckParams) -> Sequence[str]:
        lines: list[str] = []
        stdev = bench.stdev()
        mean = bench.mean()
        rate = stdev / mean
        if rate >= check_params.stdev_rel_threshold:
            lines.append(
                f"the relative standard deviation is {rate:.1%},"
                f" max allowed is {check_params.stdev_rel_threshold:.0%}",
            )
        return lines

    def check_results(self, *, local_id_list: bool = False):
        lines = []
        schemas_with_warnings = []
        for schema in self.accessor.schemas:
            warnings = self.get_warnings(schema)
            if warnings is None:
                lines.append(f"Result file of {self.accessor.get_id(schema)!r}")
                lines.append("")
                schemas_with_warnings.append(schema)
            elif warnings:
                lines.append(self.accessor.get_id(schema))
                lines.extend(warnings)
                schemas_with_warnings.append(schema)

        if local_id_list:
            print(json.dumps([self.accessor.get_local_id(schema) for schema in schemas_with_warnings]))
        else:
            print("\n".join(lines))


class BenchRunner:
    def __init__(self, accessor: BenchAccessor, checker: BenchChecker):
        self.accessor = accessor
        self.checker = checker

    def add_arguments(self, parser: ArgumentParser) -> None:
        selective_group = parser.add_mutually_exclusive_group()
        selective_group.add_argument("--include", "-i", action="extend", nargs="+", required=False)
        selective_group.add_argument("--exclude", "-e", action="extend", nargs="+", required=False)

        scope_group = parser.add_mutually_exclusive_group()
        scope_group.add_argument(
            "--missing", action="store_true", required=False, default=False,
            help="run only missing benchmarks",
        )
        scope_group.add_argument(
            "--unstable", action="store_true", required=False, default=False,
            help="run only unstable or missing benchmarks",
        )

    def run_benchmarks(
        self,
        *,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        missing: bool = False,
        unstable: bool = False,
    ) -> None:
        schemas: Sequence[BenchSchema]
        if missing:
            schemas = [
                schema for schema in self.accessor.schemas
                if self.accessor.get_case_result(schema) is not None
            ]
        elif unstable:
            schemas = [
                schema for schema, warnings in (
                    (schema, self.checker.get_warnings(schema))
                    for schema in self.accessor.schemas
                )
                if warnings is None or warnings
            ]
        else:
            schemas = self.accessor.schemas

        local_id_to_schema = {
            self.accessor.get_local_id(schema): schema
            for schema in schemas
        }

        benchmarks_to_run: list[str]
        if exclude is not None:
            benchmarks_to_run = [
                self.accessor.get_local_id(schema)
                for schema in schemas
                if self.accessor.get_local_id(schema) not in set(exclude)
            ]
        elif include is not None:
            wild_local_ids = set(include) - local_id_to_schema.keys()
            if wild_local_ids:
                raise ValueError(f"Unknown local ids {wild_local_ids}")
            benchmarks_to_run = list(include)
        else:
            benchmarks_to_run = [self.accessor.get_local_id(schema) for schema in schemas]

        print("Benchmarks to run: " + " ".join(benchmarks_to_run))
        for tag in benchmarks_to_run:
            self.run_one_benchmark(local_id_to_schema[tag])

    def run_one_benchmark(self, schema: BenchSchema) -> None:
        distributions = {
            dist: importlib.metadata.version(dist)
            for dist in schema.used_distributions
        }
        bench_id = self.accessor.get_id(schema)
        sig = inspect.signature(
            load_by_object_ref(schema.entry_point)
            if isinstance(schema.entry_point, str) else
            schema.entry_point,
        )
        with TemporaryDirectory() as dir_name:
            temp_file = Path(dir_name) / f"{bench_id}.json"
            print(f"start: {bench_id}")
            self.launch_benchmark(
                bench_name=bench_id,
                entrypoint=(
                    schema.entry_point
                    if isinstance(schema.entry_point, str) else
                    get_function_object_ref(schema.entry_point)
                ),
                params=[schema.kwargs[param] for param in sig.parameters],
                extra_args=["-o", str(temp_file)],
            )
            case_result: BenchCaseResult = json.loads(temp_file.read_text())
            case_result["pybench_data"] = {
                "case_id": self.accessor.get_id(schema),
                "base": schema.base,
                "tags": schema.tags,
                "env_spec": self.accessor.env_spec,
                "kwargs": schema.kwargs,
                "distributions": distributions,
            }
            bench = pyperf.Benchmark.loads(
                json.dumps(case_result, ensure_ascii=False, check_circular=False),
            )
            check_params = self.accessor.resolve_check_params(schema)
            stats: BenchCaseResultStats = {
                "mean": bench.mean(),
                "stdev": bench.stdev(),
                "rel_stdev": bench.stdev() / bench.mean(),
            }
            print(
                f"Relative stdev is {stats['rel_stdev']:.1%}"
                f" (max allowed is {check_params.stdev_rel_threshold:.1%})"
                "\n",
            )
            self.accessor.write_case_result(case_result, stats)

    def launch_benchmark(
        self,
        bench_name: str,
        entrypoint: str,
        params: list[Any],
        extra_args: Iterable[str] = (),
    ) -> None:
        subprocess.run(
            [
                sys.executable, "-m", "benchmarks.pybench.pyperf_runner",
                "--inherit-environ", "PYBENCH_NAME,PYBENCH_ENTRYPOINT,PYBENCH_PARAMS",
                *extra_args,
            ],
            env={
                **os.environ,
                "PYBENCH_NAME": bench_name,
                "PYBENCH_ENTRYPOINT": entrypoint,
                "PYBENCH_PARAMS": json.dumps(params),
            },
            check=True,
        )


T = TypeVar("T")


def call_by_namespace(func: Callable[..., T], namespace: Namespace) -> T:
    sig = inspect.signature(func)
    kwargs_for_func = (vars(namespace).keys() & sig.parameters.keys())
    return func(**{key: getattr(namespace, key) for key in kwargs_for_func})


BD = TypeVar("BD", bound="BenchmarkDirector")


class BenchmarkDirector:
    def __init__(
        self,
        *,
        benchmark: str,
        env_spec: EnvSpec,
        check_params: Callable[[EnvSpec], CheckParams],
        schemas: Iterable[BenchSchema] = (),
    ):
        self.benchmark = benchmark
        self.env_spec = env_spec
        self.schemas: list[BenchSchema] = list(schemas)
        self.check_params = check_params
        self.storage: BenchStorage = UninitedBenchStorage()

    def add(self, *schemas: BenchSchema) -> None:
        self.schemas.extend(schemas)

    def add_iter(self, schemas: Iterable[BenchSchema]) -> None:
        self.schemas.extend(schemas)

    def cli(self, args: Optional[Sequence[str]] = None):
        accessor = self.make_accessor()
        self._validate_schemas(accessor)

        checker = self.make_bench_checker(accessor)
        runner = self.make_bench_runner(accessor, checker)
        storage_factory = self.make_storage_factory()

        parser = self._make_parser(accessor, runner, checker, storage_factory)
        namespace = parser.parse_args(args)

        accessor.set_storage(call_by_namespace(storage_factory.create, namespace))
        call_by_namespace(accessor.override_state, namespace)
        if namespace.command == "run":
            call_by_namespace(runner.run_benchmarks, namespace)
        elif namespace.command == "check":
            call_by_namespace(checker.check_results, namespace)
        else:
            raise TypeError

    def _make_parser(
        self,
        accessor: BenchAccessor,
        runner: BenchRunner,
        checker: BenchChecker,
        storage_factory: BenchStorageFactory,
    ) -> ArgumentParser:
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(required=True)

        run_parser = subparsers.add_parser("run")
        run_parser.set_defaults(command="run")
        accessor.add_arguments(run_parser)
        runner.add_arguments(run_parser)
        storage_factory.add_arguments(run_parser)

        check_parser = subparsers.add_parser("check")
        check_parser.set_defaults(command="check")
        accessor.add_arguments(check_parser)
        checker.add_arguments(check_parser)
        storage_factory.add_arguments(check_parser)
        return parser

    def make_accessor(self) -> BenchAccessor:
        return BenchAccessor(
            benchmark=self.benchmark,
            env_spec=self.env_spec,
            check_params=self.check_params,
            schemas=self.schemas,
            storage=self.storage,
        )

    def make_storage_factory(self) -> BenchStorageFactory:
        return BenchStorageFactory(self.benchmark)

    def make_bench_runner(self, accessor: BenchAccessor, checker: BenchChecker) -> BenchRunner:
        return BenchRunner(accessor, checker)

    def make_bench_checker(self, accessor: BenchAccessor) -> BenchChecker:
        return BenchChecker(accessor)

    def _validate_schemas(self, accessor: BenchAccessor):
        local_id_set: set[str] = set()
        for schema in self.schemas:
            local_id = accessor.get_local_id(schema)
            if local_id in local_id_set:
                raise ValueError(f"Local id {local_id} is duplicated")
            local_id_set.add(local_id)

    def replace(self: BD, *, env_spec: EnvSpec, storage: BenchStorage) -> BD:
        self_copy = copy(self)
        self_copy.env_spec = env_spec
        self_copy.storage = storage
        return self_copy
