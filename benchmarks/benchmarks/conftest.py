import sys

if sys.implementation.name == "pypy":
    collect_ignore = ["bench_backend_matrix.py", "bench_backend_stress.py", "bench_backend_types.py"]
