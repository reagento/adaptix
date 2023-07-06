import concurrent
import importlib
import inspect
import json
import subprocess
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, DefaultDict, Dict, Iterable, List, Mapping, Optional, Sequence, Set, TypeVar, Union
from zipfile import ZIP_BZIP2, ZipFile

import plotly
import plotly.graph_objects as go
import pyperf

from adaptix._internal.utils import pairs
from benchmarks.pybench.director_api import BenchAccessor, BenchChecker, BenchmarkDirector

T = TypeVar('T')


def call_by_namespace(func: Callable[..., T], namespace: Namespace) -> T:
    sig = inspect.signature(func)
    kwargs_for_func = (vars(namespace).keys() & sig.parameters.keys())
    return func(**{key: getattr(namespace, key) for key in kwargs_for_func})


class Foundation(ABC):
    def print(self, *args: str):
        print(*args)

    def run(self, command: str) -> None:
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


@dataclass(frozen=True)
class EnvDescription:
    key: str
    title: str
    tox_env: str


@dataclass
class BenchmarkMeasure:
    base: str
    tags: Sequence[str]
    kwargs: Mapping[str, Any]
    distributions: Mapping[str, str]
    pyperf: pyperf.Benchmark


class AxisBounder(ABC):
    @abstractmethod
    def get_hub_x_bound(self, env_to_measures: Mapping[EnvDescription, Sequence[BenchmarkMeasure]]) -> float:
        pass


class ClusterAxisBounder(AxisBounder):
    def __init__(self, last_cluster_idx: int, boundary_rate: float):
        self.last_cluster_idx = last_cluster_idx
        self.boundary_rate = boundary_rate

    def _split_into_clusters(self, measures: Iterable[BenchmarkMeasure]) -> Sequence[Sequence[BenchmarkMeasure]]:
        clusters: List[List[BenchmarkMeasure]] = []
        current_cluster: List[BenchmarkMeasure] = []
        for prev, current in pairs(measures):
            if current.pyperf.mean() / prev.pyperf.mean() >= self.boundary_rate:
                clusters.append(current_cluster)
                current_cluster = [current]
            else:
                current_cluster.append(current)
        clusters.append(current_cluster)
        return clusters

    def get_hub_x_bound(self, env_to_measures: Mapping[EnvDescription, Sequence[BenchmarkMeasure]]) -> float:
        max_bound_value = max(
            self._split_into_clusters(measures)[self.last_cluster_idx][-1].pyperf.mean()
            for measures in env_to_measures.values()
        )
        return max_bound_value * 10 ** 6 * 1.08


@dataclass(frozen=True)
class HubDescription:
    key: str
    module: str
    title: str
    x_bounder: AxisBounder


BENCHMARK_ENVS: Iterable[EnvDescription] = [
    EnvDescription(
        title='CPython 3.8',
        key='py38',
        tox_env='py38-bench',
    ),
    EnvDescription(
        title='CPython 3.9',
        key='py39',
        tox_env='py39-bench',
    ),
    EnvDescription(
        title='CPython 3.10',
        key='py310',
        tox_env='py310-bench',
    ),
    EnvDescription(
        title='CPython 3.11',
        key='py311',
        tox_env='py311-bench',
    ),
    EnvDescription(
        title='PyPy 3.8',
        key='pypy38',
        tox_env='pypy38-bench',
    ),
]
KEY_TO_ENV = {
    env_description.key: env_description
    for env_description in BENCHMARK_ENVS
}

BENCHMARK_HUBS: Iterable[HubDescription] = [
    HubDescription(
        key='small_structures-loading',
        title='Small Structures (loading)',
        module='benchmarks.small_structures.hub_loading',
        x_bounder=ClusterAxisBounder(
            last_cluster_idx=-2,
            boundary_rate=2,
        )
    ),
    HubDescription(
        key='small_structures-dumping',
        title='Small Structures (dumping)',
        module='benchmarks.small_structures.hub_dumping',
        x_bounder=ClusterAxisBounder(
            last_cluster_idx=-3,
            boundary_rate=2,
        )
    ),
    HubDescription(
        key='gh_issues-loading',
        title='Github Issues (loading)',
        module='benchmarks.gh_issues.hub_loading',
        x_bounder=ClusterAxisBounder(
            last_cluster_idx=-2,
            boundary_rate=2,
        )
    ),
    HubDescription(
        key='gh_issues-dumping',
        title='Github Issues (dumping)',
        module='benchmarks.gh_issues.hub_dumping',
        x_bounder=ClusterAxisBounder(
            last_cluster_idx=-3,
            boundary_rate=2,
        )
    ),
]
KEY_TO_HUB = {
    hub_description.key: hub_description
    for hub_description in BENCHMARK_HUBS
}


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

    def _submit_python(
        self,
        executor: Executor,
        env_description: EnvDescription,
        code: str,
    ) -> concurrent.futures.Future[str]:
        return executor.submit(
            lambda: self.call(
                f"tox exec -e {env_description.tox_env} --skip-pkg-install -qq -- python -c '{code}'"
            ),
        )

    def load_directors(
        self,
        hub_descriptions: Iterable[HubDescription],
    ) -> Mapping[HubDescription, Mapping[EnvDescription, BenchmarkDirector]]:
        env_spec_printers = [
            dedent(
                f"""
                    import json
                    from {hub_description.module} import director
                    print(json.dumps(director.env_spec))
                """
            )
            for hub_description in hub_descriptions
        ]
        with ThreadPoolExecutor() as executor:
            hub_to_env_to_future = {
                hub_description: {
                    env_description: self._submit_python(executor, env_description, env_spec_printer)
                    for env_description in BENCHMARK_ENVS
                }
                for hub_description, env_spec_printer in zip(hub_descriptions, env_spec_printers)
            }
            return {
                hub_description: {
                    env_description: (
                        importlib.import_module(hub_description.module).director.replace(
                            env_spec=json.loads(future.result())
                        )
                    )
                    for env_description, future in env_to_future.items()
                }
                for hub_description, env_to_future in hub_to_env_to_future.items()
            }


@dataclass
class CaseState:
    director: BenchmarkDirector
    accessor: BenchAccessor
    checker: BenchChecker
    local_ids_with_warnings: Sequence[str]
    tries_count: int = 0

    @property
    def is_completed(self) -> bool:
        return not self.local_ids_with_warnings


class Orchestrator(HubProcessor):
    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            '--series',
            action='store',
            required=False,
            type=int,
            default=2,
        )

    def __init__(
        self,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        series: int = 2
    ):
        super().__init__(include=include, exclude=exclude)
        self.series = series

    def start(self) -> None:
        self.print('Start environments preparation')
        joined_envs = ",".join(env_description.tox_env for env_description in BENCHMARK_ENVS)
        self.run(f'tox --notest -p auto -e {joined_envs}')

        self.print('Loading all cases')
        hub_to_env_to_case_state: Dict[HubDescription, Dict[EnvDescription, CaseState]] = {}
        for hub_description, env_to_director in self.load_directors(self.filtered_hubs()).items():
            env_to_case_state = {}
            for env_description, director in env_to_director.items():
                accessor = director.make_accessor()
                case_state = CaseState(
                    director=director,
                    accessor=accessor,
                    checker=director.make_bench_checker(accessor),
                    local_ids_with_warnings=(),
                )
                self.update_local_ids_with_warnings(case_state)
                env_to_case_state[env_description] = case_state

            hub_to_env_to_case_state[hub_description] = env_to_case_state

        self.process_all_cases(hub_to_env_to_case_state)

    def _render_cases_to_complete(
        self,
        hub_to_env_to_case_state: Mapping[HubDescription, Mapping[EnvDescription, CaseState]],
    ) -> str:
        hub_to_env_to_case_state = {
            hub_description: env_to_case_state
            for hub_description, env_to_case_state in hub_to_env_to_case_state.items()
            if any(not case_state.is_completed for case_state in env_to_case_state.values())
        }
        hub_max_size = max(
            len(hub_description.key)
            for hub_description in hub_to_env_to_case_state.keys()
        )
        env_max_size = max(
            len(env_description.key)
            for env_to_case_state in hub_to_env_to_case_state.values()
            for env_description in env_to_case_state.keys()
        )
        return '\n'.join(
            f'{hub_description.key.rjust(hub_max_size)} tries:  '
            + '  '.join(
                f'{env_description.key.ljust(env_max_size)} - {case_state.tries_count:<2}'
                for env_description, case_state in env_to_case_state.items()
                if not case_state.is_completed
            )
            for hub_description, env_to_case_state in hub_to_env_to_case_state.items()
        )

    def process_all_cases(
        self,
        hub_to_env_to_case_state: Mapping[HubDescription, Mapping[EnvDescription, CaseState]],
    ):
        while True:
            has_uncompleted = False
            for hub_description, env_to_case_state in hub_to_env_to_case_state.items():
                for env_description, case_state in env_to_case_state.items():
                    if case_state.is_completed:
                        continue

                    has_uncompleted = True
                    cases_to_complete = (
                        '\n' + self._render_cases_to_complete(hub_to_env_to_case_state)
                    ).replace('\n', '\n  ')
                    self.print('Cases to complete:' + cases_to_complete)
                    self.print()

                    self.run_case(hub_description, env_description, case_state)

            if not has_uncompleted:
                return

    def update_local_ids_with_warnings(self, case_state: CaseState) -> None:
        local_ids_with_warnings = []
        for schema in case_state.accessor.schemas:
            warnings = case_state.checker.get_warnings(schema)
            if warnings is None or warnings:
                local_ids_with_warnings.append(
                    case_state.accessor.get_local_id(schema)
                )

        case_state.local_ids_with_warnings = local_ids_with_warnings

    def run_case(self, hub_description: HubDescription, env_description: EnvDescription, case_state: CaseState) -> None:
        hub_module = hub_description.module
        env = env_description.key
        for _ in range(self.series):
            self.print(f'Running   hub: {hub_description.key:<30} env: {env}')
            self.run(f'tox exec -e {env} --skip-pkg-install -- python -m {hub_module} run --unstable')
            case_state.tries_count += 1
            self.update_local_ids_with_warnings(case_state)
            if case_state.is_completed:
                self.run(f'tox exec -e {env} --skip-pkg-install -- python -m {hub_module} render')
                return
            self.print('Got unstable results for ' + ' '.join(case_state.local_ids_with_warnings))
            if case_state.tries_count >= 5:
                self.print(f'WARNING: too many tries to get stable benchmark results -- {case_state.tries_count}')


class Renderer(HubProcessor):
    def start(self) -> None:
        for hub_description, env_to_director in self.load_directors(self.filtered_hubs()).items():
            self.render_hub_from_directors(hub_description, env_to_director)

    def _director_to_measures(self, director: BenchmarkDirector) -> Sequence[BenchmarkMeasure]:
        accessor = director.make_accessor()
        measures = []
        for schema in accessor.schemas:
            path = accessor.bench_result_file(accessor.get_id(schema))
            measures.append(
                self._pyperf_bench_to_measure(path.read_text())
            )
        measures.sort(key=lambda x: x.pyperf.mean())
        return measures

    def _pyperf_bench_to_measure(self, data: Union[str, bytes]) -> BenchmarkMeasure:
        pybench_data = json.loads(data)['pybench_data']
        return BenchmarkMeasure(
            base=pybench_data['base'],
            tags=pybench_data['tags'],
            kwargs=pybench_data['kwargs'],
            distributions=pybench_data['distributions'],
            pyperf=pyperf.Benchmark.loads(data)
        )

    def _release_zip_to_measures(
        self,
        hub_description: HubDescription,
    ) -> Mapping[EnvDescription, Sequence[BenchmarkMeasure]]:
        with ZipFile(RELEASE_DATA / f'{hub_description.key}.zip') as release_zip:
            index = json.loads(release_zip.read('index.json'))
            env_to_files = {
                KEY_TO_ENV[env_key]: files
                for env_key, files in index['env_files'].items()
            }
            return {
                env: sorted(
                    (
                        self._pyperf_bench_to_measure(release_zip.read(file))
                        for file in files
                    ),
                    key=lambda x: x.pyperf.mean()
                )
                for env, files in env_to_files.items()
            }

    def render_hub_from_directors(
        self,
        hub_description: HubDescription,
        env_to_director: Mapping[EnvDescription, BenchmarkDirector],
    ) -> None:
        env_to_measures = {
            env_description: self._director_to_measures(director)
            for env_description, director in env_to_director.items()
        }
        figure = self.create_hub_plot(hub_description, env_to_measures)
        plotly.offline.plot(figure, config={'displaylogo': False}, filename=f'{hub_description.key}.html')

    def render_hub_from_release(
        self,
        hub_description: HubDescription,
    ) -> Mapping:
        figure = self.create_hub_plot(hub_description, self._release_zip_to_measures(hub_description))
        return figure.to_dict()

    BASE_RENAMING = {
        'pydantic': 'pydantic v2'
    }

    def _get_label(self, measure: BenchmarkMeasure) -> str:
        base = self.BASE_RENAMING.get(measure.base) or measure.base
        if measure.tags:
            tags_str = ', '.join(measure.tags)
            return f"{base}<br>({tags_str})"
        return base

    def _create_bar_chart(self, measures: Sequence[BenchmarkMeasure]) -> go.Bar:
        return go.Bar(
            x=[
                measure.pyperf.mean() * 10 ** 6
                for measure in measures
            ],
            y=[
                self._get_label(measure)
                for measure in measures
            ],
            error_x={
                'type': 'data',
                'array': [
                    measure.pyperf.stdev() * 10 ** 6
                    for measure in measures
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
                    'base': measure.base,
                    'rel_error': measure.pyperf.stdev() / measure.pyperf.mean() * 100,
                    'kwargs': '<br>'.join(
                        f'{key}={value}'
                        for key, value in measure.kwargs.items()
                    ),
                }
                for measure in measures
            ],
        )

    def create_hub_plot(
        self,
        hub_description: HubDescription,
        env_to_measures: Mapping[EnvDescription, Sequence[BenchmarkMeasure]],
    ) -> go.Figure:
        bar_charts = [
            self._create_bar_chart(measures).update(visible=False)
            for measures in env_to_measures.values()
        ]
        visible_by_default = next(
            idx for idx, env_description in enumerate(BENCHMARK_ENVS)
            if env_description.key == 'py311'
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
        height = max(len(measures) for accessor, measures in env_to_measures.items()) * 40 + 185
        # pylint: disable=no-member
        figure = go.Figure(
            bar_charts
        ).update_layout(
            title={
                'text': f"<b>{hub_description.title}</b>",
                'x': 0.5,
                'y': 0.97,
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
            range=[0, hub_description.x_bounder.get_hub_x_bound(env_to_measures)],
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
                    'y': 1 + (64 / height),
                    'xanchor': 'center',
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
        hub_to_director_to_env = self.load_directors(hub_descriptions)
        errors: List[str] = []
        errors.extend(self._validate_distributions(hub_to_director_to_env))
        return errors

    def _validate_distributions(
        self,
        hub_to_director_to_env: Mapping[HubDescription, Mapping[EnvDescription, BenchmarkDirector]],
    ) -> Sequence[str]:
        dist_to_versions: DefaultDict[str, Set[str]] = defaultdict(set)
        for _hub_description, env_to_director in hub_to_director_to_env.items():
            for director in env_to_director.values():
                accessor = director.make_accessor()
                for schema in accessor.schemas:
                    bench_report = json.loads(
                        accessor.bench_result_file(accessor.get_id(schema)).read_text()
                    )
                    for dist, version in bench_report['pybench_data']['distributions'].items():
                        dist_to_versions[dist].add(version)

        return [
            f'Benchmarks using distribution {dist!r} were taken with different versions {versions!r}'
            for dist, versions in dist_to_versions.items()
            if len(versions) > 1
        ]


RELEASE_DATA = Path(__file__).parent.parent / 'benchmarks' / 'release_data'


class Releaser(HubProcessor):
    def start(self) -> None:
        validator = HubValidator()
        validator.validate(self.filtered_hubs())
        self._release()

    def _release(self):
        hub_to_director_to_env = self.load_directors(self.filtered_hubs())
        for hub_description, env_to_director in hub_to_director_to_env.items():
            env_with_accessor = [
                (env_description, director.make_accessor())
                for env_description, director in env_to_director.items()
            ]
            env_to_files = {
                env_description: [
                    accessor.bench_result_file(accessor.get_id(schema))
                    for schema in accessor.schemas
                ]
                for env_description, accessor in env_with_accessor
            }
            with ZipFile(
                file=RELEASE_DATA / f'{hub_description.key}.zip',
                mode='w',
                compression=ZIP_BZIP2,
                compresslevel=9,
            ) as release_zip:
                for file_path in chain.from_iterable(env_to_files.values()):
                    release_zip.write(file_path, arcname=file_path.name)

                release_zip.writestr(
                    'index.json',
                    json.dumps(
                        self._get_index_data(env_to_files)
                    )
                )

    def _get_index_data(self, env_to_files: Mapping[EnvDescription, Iterable[Path]]) -> Dict[str, Any]:
        return {
            'env_files': {
                env_description.key: [
                    file.name for file in files
                ]
                for env_description, files in env_to_files.items()
            }
        }


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
