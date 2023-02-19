from setuptools import find_packages, setup

setup(
    name='benchmarks',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': [
            'pybench_pyperf_runner = benchmarks.pybench.pyperf_runner:main',
        ]
    }
)
