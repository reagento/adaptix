import sys
from pathlib import Path

from benchmarks.gh_issues import (
    bench_adaptix,
    bench_asdict,
    bench_cattrs,
    bench_dataclass_factory,
    bench_marshmallow,
    bench_mashumaro,
    bench_msgspec,
    bench_pydantic,
    bench_schematics,
)
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, PlotParams

director = BenchmarkDirector(
    data_dir=Path(__file__).parent.parent.parent / 'data' / 'gh_issues' / 'dumping',
    plot_params=PlotParams(
        title='GitHub Issues (dumping)',
        fig_size=(9, 6),
        label_padding=40,
        trim_after=600,
    ),
    env_spec={
        'py': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'py_impl': sys.implementation.name,
    },
)

director.add(
    BenchSchema(
        func=bench_adaptix.bench_dumping,
        base='adaptix',
        tags=['dp'],
        kwargs={'debug_path': True},
    ),
    BenchSchema(
        func=bench_adaptix.bench_dumping,
        base='adaptix',
        tags=[],
        kwargs={'debug_path': False},
    ),
)

director.add(
    BenchSchema(
        func=bench_mashumaro.bench_dumping,
        base='mashumaro',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_pydantic.bench_dumping,
        base='pydantic',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_asdict.bench_dumping,
        base='asdict',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_cattrs.bench_dumping,
        base='cattrs',
        tags=['dv'],
        kwargs={'detailed_validation': True},
    ),
    BenchSchema(
        func=bench_cattrs.bench_dumping,
        base='cattrs',
        tags=[],
        kwargs={'detailed_validation': False},
    ),
)

director.add(
    BenchSchema(
        func=bench_schematics.bench_dumping,
        base='schematics',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_dataclass_factory.bench_dumping,
        base='dataclass_factory',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_marshmallow.bench_dumping,
        base='marshmallow',
        tags=[],
        kwargs={},
    ),
)

director.add(
    BenchSchema(
        func=bench_msgspec.bench_dumping,
        base='msgspec',
        tags=[],
        kwargs={'no_gc': False},
    ),
    BenchSchema(
        func=bench_msgspec.bench_dumping,
        base='msgspec',
        tags=['no_gc'],
        kwargs={'no_gc': True},
    ),
)

if __name__ == '__main__':
    director.cli()
