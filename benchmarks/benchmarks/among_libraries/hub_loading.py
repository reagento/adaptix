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
        base_id='adaptix',
        label='adaptix\n(sc, dp)',
        tag='adaptix-sc-dp',
        func=bench_adaptix.bench_loading,
        kwargs={'strict_coercion': True, 'debug_path': True, 'reviews_count': 100},
        data_renaming={'strict_coercion': 'sc', 'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='adaptix',
        label='adaptix\n(sc)',
        tag='adaptix-sc',
        func=bench_adaptix.bench_loading,
        kwargs={'strict_coercion': True, 'debug_path': False, 'reviews_count': 100},
        data_renaming={'strict_coercion': 'sc', 'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='adaptix',
        label='adaptix\n(dp)',
        tag='adaptix-dp',
        func=bench_adaptix.bench_loading,
        kwargs={'strict_coercion': False, 'debug_path': True, 'reviews_count': 100},
        data_renaming={'strict_coercion': 'sc', 'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='adaptix',
        label='adaptix',
        tag='adaptix',
        func=bench_adaptix.bench_loading,
        kwargs={'strict_coercion': False, 'debug_path': False, 'reviews_count': 100},
        data_renaming={'strict_coercion': 'sc', 'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='mashumaro',
        label='mashumaro',
        tag='mashumaro',
        func=bench_mashumaro.bench_loading,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='pydantic',
        label='pydantic\n(st)',
        tag='pydantic-st',
        func=bench_pydantic.bench_loading,
        kwargs={'reviews_count': 100, 'strict_types': True},
        data_renaming={'reviews_count': 'rc', 'strict_types': 'st'},
    ),
    BenchSchema(
        base_id='pydantic',
        label='pydantic',
        tag='pydantic',
        func=bench_pydantic.bench_loading,
        kwargs={'reviews_count': 100, 'strict_types': False},
        data_renaming={'reviews_count': 'rc', 'strict_types': 'st'},
    ),
)

director.add(
    BenchSchema(
        base_id='cattrs',
        label='cattrs\n(dv)',
        tag='cattrs-dv',
        func=bench_cattrs.bench_loading,
        kwargs={'detailed_validation': True, 'reviews_count': 100},
        data_renaming={'detailed_validation': 'dv', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='cattrs',
        label='cattrs',
        tag='cattrs',
        func=bench_cattrs.bench_loading,
        kwargs={'detailed_validation': False, 'reviews_count': 100},
        data_renaming={'detailed_validation': 'dv', 'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='schematics',
        label='schematics',
        tag='schematics',
        func=bench_schematics.bench_loading,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='dataclass_factory',
        label='dataclass_factory\n(dp)',
        tag='dataclass_factory-dp',
        func=bench_dataclass_factory.bench_loading,
        kwargs={'debug_path': True, 'reviews_count': 100},
        data_renaming={'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='dataclass_factory',
        label='dataclass_factory',
        tag='dataclass_factory',
        func=bench_dataclass_factory.bench_loading,
        kwargs={'debug_path': False, 'reviews_count': 100},
        data_renaming={'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='marshmallow',
        label='marshmallow',
        tag='marshmallow',
        func=bench_marshmallow.bench_loading,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='msgspec',
        label='msgspec',
        tag='msgspec',
        func=bench_msgspec.bench_loading,
        kwargs={'no_gc': False, 'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='msgspec',
        label='msgspec\n(no_gc)',
        tag='msgspec-no_gc',
        func=bench_msgspec.bench_loading,
        kwargs={'no_gc': True, 'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

if __name__ == '__main__':
    director.cli()
