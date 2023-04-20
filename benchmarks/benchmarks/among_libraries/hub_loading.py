import sys
from pathlib import Path

from benchmarks.among_libraries import (
    bench_adaptix,
    bench_cattrs,
    bench_dataclass_factory,
    bench_marshmallow,
    bench_mashumaro,
    bench_msgspec,
    bench_pydantic,
    bench_schematics,
)
from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, PlotParams

REVIEWS_COUNT = 100

director = BenchmarkDirector(
    data_dir=Path(__file__).parent.parent.parent / 'data' / 'among_libraries' / 'loading',
    plot_params=PlotParams(
        title='Among Libraries Benchmark (loading)',
        fig_size=(9, 7.5),
        label_padding=40,
        trim_after=300,
    ),
    env_spec={
        'py': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'py_impl': sys.implementation.name,
    },
)

director.add(
    BenchSchema(
        func=bench_adaptix.bench_loading,
        base='adaptix',
        tags=['sc', 'dp'],
        kwargs={'strict_coercion': True, 'debug_path': True, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_adaptix.bench_loading,
        base='adaptix',
        tags=['sc'],
        kwargs={'strict_coercion': True, 'debug_path': False, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_adaptix.bench_loading,
        base='adaptix',
        tags=['dp'],
        kwargs={'strict_coercion': False, 'debug_path': True, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_adaptix.bench_loading,
        base='adaptix',
        tags=[],
        kwargs={'strict_coercion': False, 'debug_path': False, 'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_mashumaro.bench_loading,
        base='mashumaro',
        tags=[],
        kwargs={'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_pydantic.bench_loading,
        base='pydantic',
        tags=['strict'],
        kwargs={'strict': True, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_pydantic.bench_loading,
        base='pydantic',
        tags=[],
        kwargs={'strict': False, 'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_cattrs.bench_loading,
        base='cattrs',
        tags=['dv'],
        kwargs={'detailed_validation': True, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_cattrs.bench_loading,
        base='cattrs',
        tags=[],
        kwargs={'detailed_validation': False, 'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_schematics.bench_loading,
        base='schematics',
        tags=[],
        kwargs={'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_dataclass_factory.bench_loading,
        base='dataclass_factory',
        tags=['dp'],
        kwargs={'debug_path': True, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_dataclass_factory.bench_loading,
        base='dataclass_factory',
        tags=[],
        kwargs={'debug_path': False, 'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_marshmallow.bench_loading,
        base='marshmallow',
        tags=[],
        kwargs={'reviews_count': REVIEWS_COUNT},
    ),
)

director.add(
    BenchSchema(
        func=bench_msgspec.bench_loading,
        base='msgspec',
        tags=[],
        kwargs={'no_gc': False, 'reviews_count': REVIEWS_COUNT},
    ),
    BenchSchema(
        func=bench_msgspec.bench_loading,
        base='msgspec',
        tags=['no_gc'],
        kwargs={'no_gc': True, 'reviews_count': REVIEWS_COUNT},
    ),
)

if __name__ == '__main__':
    director.cli()
