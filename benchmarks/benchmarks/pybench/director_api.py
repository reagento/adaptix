# pylint: disable=import-error,no-name-in-module
import inspect
import json
import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import pyperf
from matplotlib import pyplot as plt
from pyperf._cli import format_checks

from benchmarks.pybench.matplotlib_utils import bar_left_aligned_label
from benchmarks.pybench.utils import get_function_object_ref

__all__ = ['BenchmarkDirector', 'BenchSchema', 'PlotParams']


@dataclass
class BenchSchema:
    func: Callable
    base: str
    tags: Iterable[str]
    kwargs: Mapping[str, Any]


@dataclass
class PlotParams:
    title: str
    fig_size: Tuple[float, float] = (8, 4.8)
    label_padding: float = 0
    trim_after: Optional[float] = None


@dataclass
class CheckParams:
    stddev_rel_threshold: float = 0.05


class BenchAccessor:
    def __init__(self, data_dir: Path, env_spec: Mapping[str, str], schemas: List[BenchSchema]):
        self.data_dir = data_dir
        self.env_spec = env_spec
        self.schemas = schemas
        self.id_to_schema: Dict[str, BenchSchema] = {self.get_id(schema): schema for schema in schemas}

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('--data-dir', action='store', required=False, type=Path)
        parser.add_argument('--env-spec', action='extend', nargs="+", required=False, metavar="KEY=VALUE")

    def override_state(self, env_spec: Optional[Iterable[str]], data_dir: Optional[Path] = None):
        if data_dir is not None:
            self.data_dir = data_dir

        if env_spec is not None:
            update_data = {}
            for item in env_spec:
                key, value = item.split('=')
                if key not in self.env_spec:
                    raise KeyError(f"Unexpected key {key}")
                update_data[key] = value
            self.env_spec = {**self.env_spec, **update_data}

    def apply_state(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def bench_result_file(self, bench_id: str) -> Path:
        return self.data_dir / f"{bench_id}.json"

    def env_spec_str(self) -> str:
        return '[' + '-'.join(f"{k}={v}" for k, v in self.env_spec.items()) + ']'

    def get_id(self, schema: BenchSchema) -> str:
        return self.get_local_id(schema) + self.env_spec_str()

    def get_local_id(self, schema: BenchSchema) -> str:
        if schema.tags:
            tags_str = '-' + '-'.join(schema.tags)
            return schema.base + tags_str
        return schema.base

    def get_label(self, schema: BenchSchema) -> str:
        if schema.tags:
            tags_str = ', '.join(schema.tags)
            return f"{schema.base}\n({tags_str})"
        return schema.base


class BenchChecker:
    def __init__(self, check_params: CheckParams, accessor: BenchAccessor):
        self.check_params = check_params
        self.accessor = accessor

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def _process_pyperf_warnings(
        self,
        schema: BenchSchema,
        bench: pyperf.Benchmark,
        warnings: Iterable[str],
    ) -> Iterable[str]:
        return [
            line
            for line in warnings
            if not line.startswith('Use')
        ]

    def get_warnings(self, schema: BenchSchema) -> Optional[Sequence[str]]:
        result_file_path = self.accessor.bench_result_file(self.accessor.get_id(schema))
        if not result_file_path.exists():
            return None

        bench = pyperf.Benchmark.load(str(result_file_path))
        warnings = self._process_pyperf_warnings(schema, bench, format_checks(bench))
        self_warnings = self._check_yourself(schema, bench)
        return [*warnings, *self_warnings]

    def _check_yourself(self, schema: BenchSchema, bench: pyperf.Benchmark) -> Sequence[str]:
        lines: List[str] = []
        stdev = bench.stdev()
        mean = bench.mean()
        percent = stdev / mean
        if percent >= self.check_params.stddev_rel_threshold:
            lines.append(
                "the relative standard deviation is {:.1%}, max allowed is {:.0%}"
                .format(
                    percent, self.check_params.stddev_rel_threshold
                )
            )
        return lines

    def check_results(self):
        lines = []
        for schema in self.accessor.schemas:
            warnings = self.get_warnings(schema)
            if warnings is None:
                lines.append(f'Result file of {self.accessor.get_id(schema)!r}')
                lines.append('')
            elif warnings:
                lines.append(self.accessor.get_id(schema))
                lines.extend(warnings)

        print('\n'.join(lines))


class BenchRunner:
    def __init__(self, accessor: BenchAccessor, checker: BenchChecker):
        self.accessor = accessor
        self.checker = checker

    def add_arguments(self, parser: ArgumentParser) -> None:
        selective_group = parser.add_mutually_exclusive_group()
        selective_group.add_argument('--include', '-i', action='extend', nargs="+", required=False)
        selective_group.add_argument('--exclude', '-e', action='extend', nargs="+", required=False)

        scope_group = parser.add_mutually_exclusive_group()
        scope_group.add_argument(
            '--missing', action='store_true', required=False, default=False,
            help='run only missing benchmarks'
        )
        scope_group.add_argument(
            '--unstable', action='store_true', required=False, default=False,
            help='run only unstable or missing benchmarks'
        )

    def run_benchmarks(
        self,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        missing: bool = False,
        unstable: bool = False,
    ) -> None:
        if missing:
            schemas = [
                schema for schema in self.accessor.schemas
                if not self.accessor.bench_result_file(self.accessor.get_id(schema)).exists()
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

        benchmarks_to_run: List[str]
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

        print('Benchmarks to run: ' + " ".join(benchmarks_to_run))
        for tag in benchmarks_to_run:
            self.run_one_benchmark(local_id_to_schema[tag])

    def run_one_benchmark(self, schema: BenchSchema) -> None:
        sig = inspect.signature(schema.func)
        bench_id = self.accessor.get_id(schema)
        result_file = self.accessor.bench_result_file(bench_id)
        with TemporaryDirectory() as dir_name:
            temp_file = Path(dir_name) / f"{bench_id}.json"
            print(f'start: {bench_id}')
            self.launch_benchmark(
                bench_name=bench_id,
                entrypoint=get_function_object_ref(schema.func),
                params=[schema.kwargs[param] for param in sig.parameters.keys()],
                extra_args=['-o', str(temp_file)]
            )
            result_file.write_text(
                json.dumps(
                    json.loads(temp_file.read_text()),
                    ensure_ascii=False,
                    indent=4,
                )
            )
            shutil.move(temp_file, result_file)

    def launch_benchmark(
        self,
        bench_name: str,
        entrypoint: str,
        params: List[Any],
        extra_args: Iterable[str] = (),
    ) -> None:
        subprocess.run(
            [
                sys.executable, '-m', 'benchmarks.pybench.pyperf_runner',
                '--inherit-environ', 'PYBENCH_NAME,PYBENCH_ENTRYPOINT,PYBENCH_PARAMS',
                *extra_args,
            ],
            env={
                **os.environ,
                'PYBENCH_NAME': bench_name,
                'PYBENCH_ENTRYPOINT': entrypoint,
                'PYBENCH_PARAMS': json.dumps(params),
            },
            check=True,
        )


class BenchPlotter:
    def __init__(self, params: PlotParams, accessor: BenchAccessor):
        self.params = params
        self.accessor = accessor

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('--output', '-o', action='store', required=False, type=Path)
        parser.add_argument('--dpi', action='store', required=False, type=float, default=100)

    def _load_benchmarks(self) -> Iterable[pyperf.Benchmark]:
        return [
            pyperf.Benchmark.load(
                str(self.accessor.bench_result_file(self.accessor.get_id(schema)))
            )
            for schema in self.accessor.schemas
        ]

    def draw_plot(self, output: Optional[Path], dpi: float):
        if output is None:
            output = self.accessor.data_dir / f'plot{self.accessor.env_spec_str()}.png'

        self._render_plot(
            output=output,
            dpi=dpi,
            benchmarks=self._load_benchmarks(),
        )

    def _render_plot(self, output: Path, dpi: float, benchmarks: Iterable[pyperf.Benchmark]) -> None:
        benchmarks = sorted(benchmarks, key=lambda b: b.mean())
        _, ax = plt.subplots(figsize=self.params.fig_size)
        x_pos = range(len(benchmarks))
        means = [bench.mean() * 10 ** 6 for bench in benchmarks]
        errors = [bench.stdev() * 10 ** 6 for bench in benchmarks]
        hbars = ax.barh(
            x_pos,
            means,
            xerr=errors,
            align='center',
            alpha=1,
            color='orange',
            ecolor='black',
            capsize=5,
            edgecolor="black",
        )

        if self.params.trim_after is not None:
            upper_bound = next(mean * 1.08 for mean in reversed(means) if mean <= self.params.trim_after)
            ax.set_xbound(upper=upper_bound)

        bar_left_aligned_label(
            ax,
            hbars,
            padding=self.params.label_padding,
            fontsize=9,
            labels=[f'{mean:.1f}' for mean in means],
        )
        ax.set_xlabel('Time (μs)')
        ax.set_yticks(x_pos)
        ax.tick_params(bottom=False, left=False)
        ax.set_yticklabels(
            [
                self.accessor.get_label(self.accessor.id_to_schema[bench.get_name()])
                for bench in benchmarks
            ]
        )
        ax.set_title(self.params.title)
        ax.xaxis.grid(True)
        plt.tight_layout(w_pad=1000)
        ax.set_axisbelow(True)
        plt.savefig(output, dpi=dpi)

def call_by_namespace(func: Callable, namespace: Namespace) -> Any:
    sig = inspect.signature(func)
    kwargs_for_func = (vars(namespace).keys() & sig.parameters.keys())
    return func(**{key: getattr(namespace, key) for key in kwargs_for_func})


class BenchmarkDirector:
    def __init__(
        self,
        data_dir: Path,
        plot_params: PlotParams,
        env_spec: Mapping[str, str],
        schemas: Iterable[BenchSchema] = (),
        check_params: CheckParams = CheckParams(),
    ):
        self.data_dir = data_dir
        self.env_spec = env_spec
        self.plot_params = plot_params
        self.schemas: List[BenchSchema] = list(schemas)
        self.check_params = check_params

    def add(self, *schemas: BenchSchema) -> None:
        self.schemas.extend(schemas)

    def cli(self, args: Optional[Sequence[str]] = None):
        accessor = self.make_accessor()
        self._validate_schemas(accessor)

        checker = self.make_bench_checker(accessor)
        runner = self.make_bench_runner(accessor, checker)
        plotter = self.make_bench_plotter(accessor)

        parser = self._make_parser(accessor, runner, plotter, checker)
        namespace = parser.parse_args(args)

        call_by_namespace(accessor.override_state, namespace)
        accessor.apply_state()
        if namespace.command == 'run':
            call_by_namespace(runner.run_benchmarks, namespace)
        elif namespace.command == 'render':
            call_by_namespace(plotter.draw_plot, namespace)
        elif namespace.command == 'run-render':
            call_by_namespace(runner.run_benchmarks, namespace)
            call_by_namespace(plotter.draw_plot, namespace)
        elif namespace.command == 'check':
            call_by_namespace(checker.check_results, namespace)
        else:
            raise TypeError

    def _make_parser(
        self,
        accessor: BenchAccessor,
        runner: BenchRunner,
        plotter: BenchPlotter,
        checker: BenchChecker,
    ) -> ArgumentParser:
        parser = ArgumentParser()

        subparsers = parser.add_subparsers(required=True)

        run_parser = subparsers.add_parser('run')
        run_parser.set_defaults(command='run')
        accessor.add_arguments(run_parser)
        runner.add_arguments(run_parser)

        render_parser = subparsers.add_parser('render')
        render_parser.set_defaults(command='render')
        accessor.add_arguments(render_parser)
        plotter.add_arguments(render_parser)

        run_render_parser = subparsers.add_parser('run-render')
        run_render_parser.set_defaults(command='run-render')
        accessor.add_arguments(run_render_parser)
        runner.add_arguments(run_render_parser)
        plotter.add_arguments(run_render_parser)

        check_parser = subparsers.add_parser('check')
        check_parser.set_defaults(command='check')
        accessor.add_arguments(check_parser)
        checker.add_arguments(check_parser)

        return parser

    def make_accessor(self) -> BenchAccessor:
        return BenchAccessor(
            data_dir=self.data_dir,
            env_spec=self.env_spec,
            schemas=self.schemas,
        )

    def make_bench_runner(self, accessor: BenchAccessor, checker: BenchChecker) -> BenchRunner:
        return BenchRunner(accessor, checker)

    def make_bench_plotter(self, accessor: BenchAccessor) -> BenchPlotter:
        return BenchPlotter(self.plot_params, accessor)

    def make_bench_checker(self, accessor: BenchAccessor) -> BenchChecker:
        return BenchChecker(self.check_params, accessor)

    def _validate_schemas(self, accessor: BenchAccessor):
        local_id_set: Set[str] = set()
        for schema in self.schemas:
            local_id = accessor.get_local_id(schema)
            if local_id in local_id_set:
                raise ValueError(f'Local id {local_id} is duplicated')
            local_id_set.add(local_id)
