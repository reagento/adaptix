import importlib
import inspect
import json
import subprocess
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable, DefaultDict, Iterable, List, NamedTuple, Optional, Sequence, Set, TypeVar
from zipfile import ZIP_BZIP2, ZipFile

import plotly
import plotly.graph_objects as go
import pyperf

from adaptix._internal.utils import pairs
from benchmarks.pybench.director_api import BenchAccessor

T = TypeVar('T')


def call_by_namespace(func: Callable[..., T], namespace: Namespace) -> T:
    sig = inspect.signature(func)
    kwargs_for_func = (vars(namespace).keys() & sig.parameters.keys())
    return func(**{key: getattr(namespace, key) for key in kwargs_for_func})


class Foundation(ABC):
    def print(self, *args: str):
        print(*args)

    def execute(self, command: str) -> None:
        subprocess.run(command, shell=True, check=True)  # nosec  # noqa: DUO116

    def call(self, command: str) -> str:
        proc = subprocess.run(command, shell=True, capture_output=True, check=True)  # nosec  # noqa: DUO116
        return proc.stdout.decode('utf-8')

    @classmethod
    @abstractmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        ...

    @abstractmethod
    def start(self) -> None:
        ...


@dataclass
class EnvDescription:
    key: str
    title: str


@dataclass
class HubDescription:
    key: str
    module: str
    title: str


BENCHMARK_ENVS: Iterable[EnvDescription] = [
    EnvDescription(
        title='CPython 3.8',
        key='py38-bench',
    ),
    EnvDescription(
        title='CPython 3.9',
        key='py39-bench',
    ),
    EnvDescription(
        title='CPython 3.10',
        key='py310-bench',
    ),
    EnvDescription(
        title='CPython 3.11',
        key='py311-bench',
    ),
    EnvDescription(
        title='PyPy 3.8',
        key='pypy38-bench',
    ),
]


BENCHMARK_HUBS: Iterable[HubDescription] = [
    HubDescription(
        key='small_structures-loading',
        title='Small Structures (loading)',
        module='benchmarks.small_structures.hub_loading',
    ),
    HubDescription(
        key='small_structures-dumping',
        title='Small Structures (dumping)',
        module='benchmarks.small_structures.hub_dumping',
    ),
    HubDescription(
        key='gh_issues-loading',
        title='Github Issues (loading)',
        module='benchmarks.gh_issues.hub_loading',
    ),
    HubDescription(
        key='gh_issues-dumping',
        title='Github Issues (dumping)',
        module='benchmarks.gh_issues.hub_dumping',
    ),
]


class HubProcessor(Foundation, ABC):
    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        selective_group = parser.add_mutually_exclusive_group()
        selective_group.add_argument(
            '--include', '-i',
            action='extend',
            nargs="+",
            required=False,
        )
        selective_group.add_argument(
            '--exclude',
            '-e',
            action='extend',
            nargs="+",
            required=False,
        )

    def __init__(
        self,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
    ):
        self.include = include
        self.exclude = exclude

    def filtered_hubs(self) -> Iterable[HubDescription]:
        if self.include:
            wild_hubs = set(self.include) - {hub_description.key for hub_description in BENCHMARK_HUBS}
            if wild_hubs:
                raise ValueError(f"Unknown hubs {wild_hubs}")
            return [
                hub_description
                for hub_description in BENCHMARK_HUBS
                if hub_description.key in self.include
            ]
        if self.exclude:
            wild_hubs = set(self.exclude) - {hub_description.key for hub_description in BENCHMARK_HUBS}
            if wild_hubs:
                raise ValueError(f"Unknown hubs {wild_hubs}")
            return [
                hub_description
                for hub_description in BENCHMARK_HUBS
                if hub_description.key not in self.exclude
            ]
        return BENCHMARK_HUBS


class Orchestrator(HubProcessor):
    def start(self):
        self.print('Start environments preparation')
        joined_envs = ",".join(env_description.key for env_description in BENCHMARK_ENVS)
        self.execute(f'tox --notest -p auto -e {joined_envs}')

        for hub_description in self.filtered_hubs():
            self.print(f'Start processing {hub_description.key}')
            for env_description in BENCHMARK_ENVS:
                self.process_env_hub(hub_description, env_description)

    def process_env_hub(self, hub_description: HubDescription, env_description: EnvDescription):
        hub_mod = hub_description.module
        env = env_description.key
        i = 0
        while True:
            self.print(f'Running   hub: {hub_description.key:<30} env: {env_description.key}')
            self.execute(f'tox exec -e {env} --skip-pkg-install -- python -m {hub_mod} run --unstable')
            id_list = json.loads(
                self.call(f'tox exec -e {env} -qq -- python -m {hub_mod} check --local-id-list')
            )
            i += 1
            if not id_list:
                self.execute(f'tox exec -e {env} --skip-pkg-install -- python -m {hub_mod} render')
                return
            self.print('Got unstable results for ' + ' '.join(id_list))
            if i >= 5:
                self.print(f'WARNING: too many tries to get stable benchmark results -- {i}')


def get_accessors_for_each_env(foundation: Foundation, hub_description: HubDescription) -> Sequence[BenchAccessor]:
    env_spec_printer = dedent(
        f"""
            import json
            from {hub_description.module} import director
            print(json.dumps(director.env_spec))
        """
    )
    executor = ThreadPoolExecutor()
    results = executor.map(
        lambda env_description: foundation.call(
            f"tox exec -e {env_description.key} --skip-pkg-install -qq -- python -c '{env_spec_printer}'"
        ),
        BENCHMARK_ENVS,
    )
    return [
        importlib.import_module(hub_description.module).director.replace(
            env_spec=json.loads(res)
        ).make_accessor()
        for res in results
    ]


class AccessorWithBenchmarks(NamedTuple):
    accessor: BenchAccessor
    benchmarks: Sequence[pyperf.Benchmark]


class Renderer(HubProcessor):
    def start(self) -> None:
        for hub_description in self.filtered_hubs():
            self.render_hub(hub_description)

    def render_hub(self, hub_description: HubDescription) -> None:
        figure = self.create_hub_plot(hub_description)
        plotly.offline.plot(figure, config={'displaylogo': False}, filename=f'{hub_description.key}.html')

    def _collect_accessors_with_benchmarks(self, hub_description: HubDescription) -> Sequence[AccessorWithBenchmarks]:
        return [
            AccessorWithBenchmarks(
                accessor,
                sorted(
                    [
                        pyperf.Benchmark.load(
                            str(accessor.bench_result_file(accessor.get_id(schema)))
                        )
                        for schema in accessor.schemas
                    ],
                    key=lambda b: b.mean()
                )
            )
            for accessor in get_accessors_for_each_env(self, hub_description)
        ]

    def _create_bar_chart(self, accessor: BenchAccessor, benchmarks: Sequence[pyperf.Benchmark]) -> go.Bar:
        return go.Bar(
            x=[
                bench.mean() * 10 ** 6
                for bench in benchmarks
            ],
            y=[
                accessor.get_label(accessor.id_to_schema[bench.get_name()]).replace('\n', '<br>')
                for bench in benchmarks
            ],
            error_x={
                'type': 'data',
                'array': [
                    bench.stdev() * 10 ** 6
                    for bench in benchmarks
                ],
                'width': 4,
                'thickness': 1.5,
                'color': 'rgba(14, 83, 125, 1.0)',
            },
            texttemplate='%{x:,.1f}',
            textposition='inside',
            insidetextanchor='start',
            insidetextfont={
                "family": 'Helvetica',
                "color": 'white'
            },
            orientation='h',
            marker={
                'color': 'rgba(129, 182, 230, 1.0)',
                'line': {
                    'color': 'rgba(17, 95, 143, 1.0)',
                    'width': 1.2,
                }
            },
            hovertemplate=(
                '<b>%{customdata.base}</b><br>'
                '%{x:,.1f} μs ± %{error_x.array:.1f} μs (%{customdata.rel_error:.1f}%)<br>'
                '<br>'
                '%{customdata.kwargs}'
                '<extra></extra>'
            ),
            customdata=[
                {
                    'base': accessor.id_to_schema[bench.get_name()].base,
                    'rel_error': bench.stdev() / bench.mean() * 100,
                    'kwargs': '<br>'.join(
                        f'{key}={value}'
                        for key, value in accessor.id_to_schema[bench.get_name()].kwargs.items()
                    ),
                }
                for bench in benchmarks
            ],
        )

    def _get_x_bound(self, accessors_with_benchmarks: Iterable[AccessorWithBenchmarks]) -> float:
        return max(
            next(
                current.mean() * 10 ** 6
                for prev, current in pairs(reversed(benchmarks))
                if prev.mean() / current.mean() >= 2
            )
            for accessor, benchmarks in accessors_with_benchmarks
        ) * 1.08

    def create_hub_plot(self, hub_description: HubDescription) -> go.Figure:
        accessors_with_benchmarks = self._collect_accessors_with_benchmarks(hub_description)
        bar_charts = [
            self._create_bar_chart(
                accessor_with_benchmarks.accessor,
                accessor_with_benchmarks.benchmarks,
            ).update(visible=False)
            for accessor_with_benchmarks in accessors_with_benchmarks
        ]
        visible_by_default = next(
            idx for idx, env_description in enumerate(BENCHMARK_ENVS)
            if env_description.key == 'py311-bench'
        )
        bar_charts[visible_by_default].update(visible=True)
        buttons = [
            {
                'args': [
                    {'visible': [env_idx == bar_idx for bar_idx in range(len(bar_charts))]}
                ],
                'label': env_description.title,
                'method': 'update',
            }
            for env_idx, env_description in enumerate(BENCHMARK_ENVS)
        ]
        height = max(len(benchmarks) for accessor, benchmarks in accessors_with_benchmarks) * 40 + 185
        # pylint: disable=no-member
        figure = go.Figure(
            bar_charts
        ).update_layout(
            title={
                'text': f"<b>{hub_description.title}</b>",
                'x': 0.97,
                'y': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {
                    'size': 18,
                },
            },
            xaxis_title="Time (μs)",
            font={
                'family': 'Helvetica',
                'size': 12,
                'color': 'Black',
            },
            template='plotly_white',
            margin_pad=10,
            hoverlabel={
                "bgcolor": 'white'
            },
        ).update_xaxes(
            range=[0, self._get_x_bound(accessors_with_benchmarks)],
        ).update_layout(
            width=1000,
            height=height,
            xaxis_fixedrange=True,
            yaxis_fixedrange=True,
            modebar_remove=['zoom', 'pan', 'select', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale', 'lasso2d']
        ).update_layout(
            updatemenus=[
                {
                    "type": 'buttons',
                    "direction": 'left',
                    "buttons": buttons,
                    "borderwidth": 0.5,
                    'bordercolor': 'black',
                    'showactive': True,
                    'active': visible_by_default,
                    'x': 0.5,
                    'xanchor': 'center',
                    'y': 1.07,
                    'yanchor': 'top',
                },
            ]
        )
        return figure


class HubValidator(HubProcessor):
    def start(self) -> None:
        errors = self.validate(self.filtered_hubs())
        if errors:
            self.print('\n'.join(errors))

    def validate(self, hub_descriptions: Iterable[HubDescription]) -> Sequence[str]:
        errors: List[str] = []

        for hub_description in hub_descriptions:
            accessors = get_accessors_for_each_env(self, hub_description)

            dist_to_versions: DefaultDict[str, Set[str]] = defaultdict(set)
            for accessor in accessors:
                for schema in accessor.schemas:
                    bench_report = json.loads(
                        accessor.bench_result_file(accessor.get_id(schema)).read_text()
                    )
                    for dist, version in bench_report['pybench_data']['distributions'].items():
                        dist_to_versions[dist].add(version)

            errors.extend(
                f'Benchmarks using distribution {dist!r} were taken with different versions {versions!r}'
                for dist, versions in dist_to_versions.items()
                if len(versions) > 1
            )

        return errors


RELEASE_DATA = Path(__file__).parent / 'benchmarks' / 'release_data'


class Releaser(HubProcessor):
    def start(self) -> None:
        validator = HubValidator()
        validator.validate(self.filtered_hubs())
        self._release()

    def _release(self):
        for hub_description in self.filtered_hubs():
            accessors = get_accessors_for_each_env(self, hub_description)
            files = sorted(
                [
                    accessor.bench_result_file(accessor.get_id(schema))
                    for accessor in accessors
                    for schema in accessor.schemas
                ],
                key=lambda p: p.name,
            )

            with ZipFile(
                file=RELEASE_DATA / f'{hub_description.key}.zip',
                mode='w',
                compression=ZIP_BZIP2,
                compresslevel=9,
            ) as release_zip:
                for file_path in files:
                    release_zip.write(file_path)


class HubListGetter(Foundation):
    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        pass

    def start(self) -> None:
        self.print('\n'.join([hub_description.key for hub_description in BENCHMARK_HUBS]))


COMMAND_TO_CLS = {
    'run': Orchestrator,
    'render': Renderer,
    'validate': HubValidator,
    'release': Releaser,
    'hub-list': HubListGetter,
}


def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(required=True)
    for command, cls in COMMAND_TO_CLS.items():
        command_parser = subparsers.add_parser(command)
        command_parser.set_defaults(command=command)
        cls.add_arguments(command_parser)

    namespace = parser.parse_args()
    cls = COMMAND_TO_CLS[namespace.command]
    instance = call_by_namespace(cls, namespace)
    instance.start()


if __name__ == '__main__':
    main()
