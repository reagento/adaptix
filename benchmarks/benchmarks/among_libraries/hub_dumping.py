import sys
from pathlib import Path

from benchmarks.among_libraries import (
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
    data_dir=Path(__file__).parent.parent.parent / 'data' / 'among_libraries' / 'dumping',
    plot_params=PlotParams(
        title='Among Libraries Benchmark (dumping)',
        fig_size=(9, 6),
        label_padding=40,
        trim_after=200,
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
        kwargs={'debug_path': True, 'reviews_count': 100},
    ),
    BenchSchema(
        func=bench_adaptix.bench_dumping,
        base='adaptix',
        tags=[],
        kwargs={'debug_path': False, 'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_mashumaro.bench_dumping,
        base='mashumaro',
        tags=[],
        kwargs={'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_pydantic.bench_dumping,
        base='pydantic',
        tags=['st'],
        kwargs={'reviews_count': 100, 'strict_types': True},
    ),
    BenchSchema(
        func=bench_pydantic.bench_dumping,
        base='pydantic',
        tags=[],
        kwargs={'reviews_count': 100, 'strict_types': False},
    ),
)

director.add(
    BenchSchema(
        func=bench_asdict.bench_dumping,
        base='asdict',
        tags=[],
        kwargs={'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_cattrs.bench_dumping,
        base='cattrs',
        tags=['dv'],
        kwargs={'detailed_validation': True, 'reviews_count': 100},
    ),
    BenchSchema(
        func=bench_cattrs.bench_dumping,
        base='cattrs',
        tags=[],
        kwargs={'detailed_validation': False, 'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_schematics.bench_dumping,
        base='schematics',
        tags=[],
        kwargs={'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_dataclass_factory.bench_dumping,
        base='dataclass_factory',
        tags=[],
        kwargs={'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_marshmallow.bench_dumping,
        base='marshmallow',
        tags=[],
        kwargs={'reviews_count': 100},
    ),
)

director.add(
    BenchSchema(
        func=bench_msgspec.bench_dumping,
        base='msgspec',
        tags=[],
        kwargs={'no_gc': False, 'reviews_count': 100},
    ),
    BenchSchema(
        func=bench_msgspec.bench_dumping,
        base='msgspec',
        tags=['no_gc'],
        kwargs={'no_gc': True, 'reviews_count': 100},
    ),
)

if __name__ == '__main__':
    director.cli()
