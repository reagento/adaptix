from setuptools import find_packages, setup

setup(
    name="benchmarks",
    version="0.0.0",
    packages=find_packages("."),
    entry_points={
        "console_scripts": [
            "bench_nexus = benchmarks.bench_nexus:main",
        ],
    },
)
