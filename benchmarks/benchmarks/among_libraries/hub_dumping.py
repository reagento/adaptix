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
        label_padding=35,
    ),
    env_spec={
        'py': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'py_impl': sys.implementation.name,
    },
)

director.add(
    BenchSchema(
        base_id='adaptix',
        label='adaptix\n(dp)',
        tag='adaptix-dp',
        func=bench_adaptix.bench_dumping,
        kwargs={'debug_path': True, 'reviews_count': 100},
        data_renaming={'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
    BenchSchema(
        base_id='adaptix',
        label='adaptix',
        tag='adaptix',
        func=bench_adaptix.bench_dumping,
        kwargs={'debug_path': False, 'reviews_count': 100},
        data_renaming={'debug_path': 'dp', 'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='mashumaro',
        label='mashumaro',
        tag='mashumaro',
        func=bench_mashumaro.bench_dumping,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='pydantic',
        label='pydantic\n(st)',
        tag='pydantic-st',
        func=bench_pydantic.bench_dumping,
        kwargs={'reviews_count': 100, 'strict_types': True},
        data_renaming={'reviews_count': 'rc', 'strict_types': 'st'},
    ),
)
director.add(
    BenchSchema(
        base_id='pydantic',
        label='pydantic',
        tag='pydantic',
        func=bench_pydantic.bench_dumping,
        kwargs={'reviews_count': 100, 'strict_types': False},
        data_renaming={'reviews_count': 'rc', 'strict_types': 'st'},
    ),
)

director.add(
    BenchSchema(
        base_id='asdict',
        label='asdict',
        tag='asdict',
        func=bench_asdict.bench_dumping,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='cattrs',
        label='cattrs\n(dv)',
        tag='cattrs-dv',
        func=bench_cattrs.bench_dumping,
        kwargs={'detailed_validation': True, 'reviews_count': 100},
        data_renaming={'detailed_validation': 'dv', 'reviews_count': 'rc'},
    ),
)
director.add(
    BenchSchema(
        base_id='cattrs',
        label='cattrs',
        tag='cattrs',
        func=bench_cattrs.bench_dumping,
        kwargs={'detailed_validation': False, 'reviews_count': 100},
        data_renaming={'detailed_validation': 'dv', 'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='schematics',
        label='schematics',
        tag='schematics',
        func=bench_schematics.bench_dumping,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='dataclass_factory',
        label='dataclass_factory',
        tag='dataclass_factory',
        func=bench_dataclass_factory.bench_dumping,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='marshmallow',
        label='marshmallow',
        tag='marshmallow',
        func=bench_marshmallow.bench_dumping,
        kwargs={'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

director.add(
    BenchSchema(
        base_id='msgspec',
        label='msgspec',
        tag='msgspec',
        func=bench_msgspec.bench_dumping,
        kwargs={'no_gc': False, 'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)
director.add(
    BenchSchema(
        base_id='msgspec',
        label='msgspec\n(no_gc)',
        tag='msgspec-no_gc',
        func=bench_msgspec.bench_dumping,
        kwargs={'no_gc': True, 'reviews_count': 100},
        data_renaming={'reviews_count': 'rc'},
    ),
)

if __name__ == '__main__':
    director.cli()
