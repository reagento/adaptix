import sys

if sys.implementation.name == "pypy":
    collect_ignore_glob = ["bench_msgspec.py"]
