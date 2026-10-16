================================
xDSL and LLVM backend experiment
================================

The experimental ``XDSLCodeGenerator`` consumes the existing native plans,
builds SSA operations in xDSL's LLVM dialect, verifies and canonicalizes them,
translates them with ``xdsl.backend.llvm.convert.convert_module``, and runs
LLVM's optimization pipeline and MCJIT through llvmlite. It emits machine code
for the host CPU. External MLIR executables, a C compiler and NASM are not
required. This evaluates the xDSL-to-LLVM path, rather than xDSL's separate
native x86 backend.

The entry point is an ordinary CPython builtin with a ``(data)`` signature.
It keeps the GIL, uses the project's versioned CPython layouts, and owns its
constants and JIT engine through ``NativeCode``. Existing x86 code can call its
raw entry without a ctypes or CFFI trampoline. The experiment is restricted to
the existing native platform: Linux x86-64 with a supported GIL-enabled release
build of CPython. It has been tested on CPython 3.13 and 3.14.

Supported fast paths are exact scalar identity checks, lists with identity
element converters, flat required scalar model loaders, and flat model dumpers
with ordinary slot descriptors. Other plans, or inputs failing a fast-path
guard, use Adaptix's Python generation and preserve its error handling. Model
loaders use a normal constructor call. Dict-based model dumpers use Python
generation. Nested models, defaults and custom converters are deliberately
outside this experiment's native subset.

The default backend and public ``CodeGenBackend`` values remain unchanged.
The experiment is injected through the existing internal dependency::

    from adaptix import Retort
    from adaptix._internal.morphing.native.codegen import NativeCodeGenRequest
    from adaptix._internal.morphing.native.xdsl.generator import XDSLCodeGenerator
    from adaptix._internal.provider.value_provider import ValueProvider

    generator = XDSLCodeGenerator(opt_level=2)
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])
    load = retort.get_loader(list[int])
    assert load([1, 2, 3]) == [1, 2, 3]

Set ``capture_artifacts=True`` when inspecting generated code. It retains
verified xDSL IR, LLVM IR before and after optimization, assembly and a
relocatable object file in ``code.memory.artifact``. Diagnostic printing and
the extra assembly/object emission are disabled in normal measurements.
The JIT entry itself remains available with diagnostics disabled.

Reproduction
============

The measured versions are xDSL 0.73.0, llvmlite 0.50.0 and its bundled LLVM
22.1.0. Install them in an isolated editable environment::

    uv venv --python 3.13 .cache/xdsl/venv
    uv pip install --python .cache/xdsl/venv/bin/python -e . -r requirements/xdsl.txt
    uv pip install --python .cache/xdsl/venv/bin/python -e tests_helpers pytest pytest-asyncio

Run the tests and benchmark::

    .cache/xdsl/venv/bin/python -m pytest tests/unit/morphing/xdsl
    .cache/xdsl/venv/bin/python benchmarks/benchmarks/bench_xdsl.py \
        --cpu 16 --rounds 9 --iterations 10000 \
        --output benchmarks/xdsl_results/cpython313.json \
        --artifacts .cache/xdsl/artifacts313

    .cache/xdsl/venv/bin/python benchmarks/benchmarks/bench_xdsl_resources.py \
        --cpu 16 --output benchmarks/xdsl_results/resources313.json
    .cache/xdsl/venv/bin/python benchmarks/benchmarks/xdsl_quality.py \
        .cache/xdsl/artifacts313 --output benchmarks/xdsl_results/quality313.json

Repeat with Python 3.14 and a separate environment and output path.
Choose a CPU in the process's allowed affinity mask. ``--smoke`` runs a small
subset. Full JSON contains individual timing samples; CSV provides a flat
comparison. Artifacts contain both the public entry and the raw entry, plus
fallback and exception paths.

Methodology
===========

Measurements run on the same ``znver5`` host, pinned to CPU 16. Each runtime
measurement is the median of nine rounds of 10,000 calls to an already-created
loader or dumper. Backend order rotates each round. Input is a Python object;
no JSON parsing or encoding is involved. Lists contain ints, or a mixture of
ints and strings for the nullable union type; tests additionally cover None.
Models are dataclasses with required int fields. Outputs are checked against
the Python backend before measurement. Microbenchmark results are local to
this machine and these inputs.

``x86`` is the current specialized backend. ``reference`` is the existing x86
encoder using the same conservative model-loading algorithm as LLVM: dict
lookups, exact scalar checks, owned arguments and a normal Python constructor
call. It only compiles model loaders. It helps separate instruction selection
and register allocation from specialized algorithms. Even this control is not
identical machine-level lowering: LLVM can inline, merge branches and
reorganize reference handling. For other cases it uses Python generation.

Creation time is the median of three new retorts and new converter builds,
after backend modules have been imported. It excludes artifact capture and
the first invocation. The resource probe separately measures imports and
process memory in fresh subprocesses. No compile-time claims include imports
unless explicitly stated.

Results
========

.. include:: ../../benchmarks/xdsl_results/report.rst

References
==========

* `xDSL's LLVM translator <https://docs.xdsl.dev/reference/backend/llvm/convert/>`__
* `xDSL's LLVM JIT backend <https://docs.xdsl.dev/reference/jit/llvm/backend/>`__
* `xDSL's native x86 backend <https://docs.xdsl.dev/reference/backend/x86/arch/>`__
