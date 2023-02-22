# pylint: disable=import-error,no-name-in-module
import inspect
import json
import os
import shutil
import subprocess
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pyperf
from matplotlib import pyplot as plt

from benchmarks.pybench.matplotlib_utils import bar_left_aligned_label
from benchmarks.pybench.utils import get_function_object_ref

__all__ = ['BenchmarkDirector', 'BenchSchema', 'PlotParams']


@dataclass
class BenchSchema:
    base_id: str
    label: str
    tag: str
    func: Callable
    kwargs: Mapping[str, Any]
    data_renaming: Mapping[str, str]


@dataclass
class PlotParams:
    title: str
    fig_size: Tuple[float, float] = (8, 4.8)
    label_padding: float = 0


class BenchAccessor:
    def __init__(self, data_dir: Path, env_spec: Mapping[str, Any], schemas: List[BenchSchema]):
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
        if schema.kwargs:
            id_kwargs = {schema.data_renaming.get(k, k): v for k, v in schema.kwargs.items()}
            kwargs_str = '-'.join(f"{k}={v}" for k, v in id_kwargs.items())
            return f"{schema.base_id}{self.env_spec_str()}[{kwargs_str}]"
        return schema.base_id


class Plotter:
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
            edgecolor="black"
        )
        bar_left_aligned_label(ax, hbars, fmt='%.1f', padding=self.params.label_padding, fontsize=9)
        ax.set_xlabel('Time (μs)')
        ax.set_yticks(x_pos)
        ax.tick_params(bottom=False, left=False)
        ax.set_yticklabels([self.accessor.id_to_schema[bench.get_name()].label for bench in benchmarks])
        ax.set_title(self.params.title)
        ax.xaxis.grid(True)
        plt.tight_layout(w_pad=1000)
        ax.set_axisbelow(True)
        plt.savefig(output, dpi=dpi)


class BenchRunner:
    def __init__(self, accessor: BenchAccessor):
        self.accessor = accessor

    def add_arguments(self, parser: ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--include', '-i', action='extend', nargs="+", required=False)
        group.add_argument('--exclude', '-e', action='extend', nargs="+", required=False)
        group.add_argument(
            '--missing', action='store_true', required=False, default=False,
            help='run only missing benchmarks'
        )

    def run_benchmarks(
        self,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        missing: bool = False,
    ) -> None:
        if not missing:
            schemas = self.accessor.schemas
        else:
            schemas = [
                schema for schema in self.accessor.schemas
                if not self.accessor.bench_result_file(self.accessor.get_id(schema)).exists()
            ]
        tag_to_schema = {
            schema.tag: schema
            for schema in schemas
        }

        benchmarks_to_run: List[str]
        if exclude is not None:
            benchmarks_to_run = [schema.tag for schema in schemas if schema.tag not in set(exclude)]
        elif include is not None:
            wild_labels = set(include) - tag_to_schema.keys()
            if wild_labels:
                raise ValueError(f"Unknown labels {wild_labels}")
            benchmarks_to_run = list(include)
        else:
            benchmarks_to_run = [schema.tag for schema in schemas]

        for tag in benchmarks_to_run:
            self.run_one_benchmark(tag_to_schema[tag])

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
                'python', '-m', 'benchmarks.pybench.pyperf_runner',
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
    ):
        self.data_dir = data_dir
        self.env_spec = env_spec
        self.plot_params = plot_params
        self.schemas: List[BenchSchema] = list(schemas)

    def add(self, *schemas: BenchSchema) -> None:
        self.schemas.extend(schemas)

    def cli(self, args: Optional[Sequence[str]] = None):
        accessor = self.make_accessor()
        runner = self.make_bench_runner(accessor)
        plotter = self.make_bench_plotter(accessor)

        parser = self._make_parser(accessor, runner, plotter)
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
        else:
            raise TypeError

    def _make_parser(self, accessor: BenchAccessor, runner: BenchRunner, plotter: Plotter) -> ArgumentParser:
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
        return parser

    def make_accessor(self) -> BenchAccessor:
        return BenchAccessor(
            data_dir=self.data_dir,
            env_spec=self.env_spec,
            schemas=self.schemas,
        )

    def make_bench_runner(self, accessor: BenchAccessor) -> BenchRunner:
        return BenchRunner(accessor)

    def make_bench_plotter(self, accessor: BenchAccessor) -> Plotter:
        return Plotter(self.plot_params, accessor)
