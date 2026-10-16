# adaptix-benchmarks-data

Raw pyperf measurements used to build the [Adaptix benchmark documentation](https://adaptix.readthedocs.io/en/latest/benchmarks.html).

The four archives were regenerated on October 11, 2026, on an AMD Ryzen 9 9950X
running Linux x86-64 under WSL2. They contain 169 cases across CPython 3.13.15
and 3.14.4. Every competing library was rerun on the same machine.

Each case uses six worker processes with five measured values and two warmup
values per worker, a minimum value duration of 50 ms, and CPU affinity 2.
Cases failing the stability checks (including the 4% relative standard deviation
limit) use ten workers with eight measured values each and a minimum value
duration of 100 ms (200 ms for marshmallow dumping on CPython 3.14). The JSON files retain pyperf metadata, individual measured values, library
versions, conversion settings, and interpreter/platform details. Chart error
bars show the standard deviation, not a confidence interval.

Marshmallow Simple Structures dumping on CPython 3.14 retains a 5.0% relative
standard deviation, mostly between worker processes, after the longer runs.
All measured worker values are retained. The other 168 cases pass the
benchmark stability checks.

These scenarios convert Python objects, excluding converter generation and
JSON parsing/encoding. Adaptix's `python` and `x86_64` tags select its two code
generation backends. Other model definitions, recipes and conversion settings
are identical between the backends. Both coercion modes and all DebugTrail
modes are included, as are the original competitor configuration variants.

The Adaptix implementation is based on
[2956c611a739b145eccbeb7781bc5b08ece57a3a](https://github.com/reagento/adaptix/commit/2956c611a739b145eccbeb7781bc5b08ece57a3a).
Native loading cases and their msgspec comparisons on both interpreters were
then remeasured with working-tree changes adding scalar field batches,
direct optional-key probes and bounded model inlining. These changes also
enable native model construction on 3.13, use its managed-dictionary setter
for wide models, and keep callable method metadata in immutable storage
through cyclic garbage collection.

The source files used for this rerun have these SHA-256 fingerprints:

| File under `src/adaptix/_internal/` | SHA-256 |
| --- | --- |
| `code_tools/x86_64_compiler.py` | `7a80bed5be173d5f5cc65a3a9ab0a8bb0e948a94b1f4dcad77f584c424692156` |
| `code_tools/native_callable.py` | `cdcf78ed386b1ff66971dde9a57cdce7fafa013bfb631ca4aee93f89e36d9138` |
| `morphing/native/x86_64/model.py` | `49d9662952c737f99e64c6f6a546c36c3b87d26a547e77fe78c50ffddd1ce8c1` |

See the benchmark modules and reproduction commands in the main Adaptix
repository for the configuration of each case.

Each ZIP contains `index.json`, which maps interpreter keys to case filenames,
and a pyperf JSON file for every measured case. Only the measured interpreter
keys `py313` and `py314` appear in the current index.

On CPython 3.14, dataclass-factory 2.16 cannot generate converters for the
GitHub Issues models. Its two loading variants and one dumping variant are
omitted on that interpreter and measured on CPython 3.13. Unsupported cases
are not assigned timings.
