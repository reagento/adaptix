==================
Contributing
==================

How to setup the repository
================================

.. warning::
    All internal tools and scripts are designed only to work on Linux.
    You have to use WSL to develop the project on Windows.


#. Install `Just <https://github.com/casey/just?tab=readme-ov-file#packages>`__

   Just is a command runner that is used here instead of ``make``.

#. Install all needed python interpreters

   * CPython 3.10
   * CPython 3.11
   * CPython 3.12
   * CPython 3.13
   * PyPy 3.10
   * PyPy 3.11

#. Clone repository with submodules

   .. code-block:: bash

      git clone --recurse-submodules https://github.com/reagento/adaptix

   If you already cloned the project and forgot ``--recurse-submodules``,
   directory ``benchmarks/release_data`` will be empty.
   You can fix it executing ``git submodule update --init --recursive``.

#. Create `venv <https://docs.python.org/3/library/venv.html>`__ and run

   .. code-block:: bash

      just bootstrap

#. Run main commands to check that everything is ok

   .. code-block:: bash

      just lint
      just test-all


Native code generation dependencies
===================================

Morphing providers request a ``NativeCodeGenerator`` through
``NativeCodeGenRequest``. The request is located, so a recipe can replace the
generator globally or for selected fields with ``bound``. A ``None`` response
keeps Python generation. Model compilation caches distinguish generators by
identity; injected implementations do not need to be hashable.

The dependency has one entry point: ``compile(plan, hook=...)``. Providers
assemble typed plans from shapes, name layouts, child converters and policies;
they do not select instruction emitters. ``native/plan.py`` defines these
plans, ``native/descriptions.py`` describes scalar conversions, and
``native/registry.py`` attaches descriptions to converters without retaining
recursive graphs. These modules also work with Python generation.

``native/runtime.py`` contains shared container error handling. Model-specific
runtime semantics remain in ``model/native_runtime.py``. Neither layer emits
instructions. Architecture-specific lowering lives in ``native/x86_64/``.

``Retort`` resolves ``CodeGenBackend`` at configuration time and supplies the
built-in implementation as a default dependency. ``X86CodeGenerator`` is the
production implementation. It receives a ``compiler_factory`` and
passes it to every x86 model and container emitter. ``X86Compiler`` in turn
receives an ``assembler_factory`` for every code fragment, including recovery
blocks, function entries and call context initialization.

For example, the dependencies can be composed explicitly through a recipe::

    from functools import partial

    from adaptix import Retort
    from adaptix._internal.code_tools.x86_64_assembler import X86Assembler
    from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
    from adaptix._internal.morphing.native.codegen import NativeCodeGenRequest
    from adaptix._internal.morphing.native.x86_64.generator import X86CodeGenerator
    from adaptix._internal.provider.value_provider import ValueProvider

    generator = X86CodeGenerator(
        compiler_factory=partial(X86Compiler, assembler_factory=X86Assembler),
    )
    retort = Retort(recipe=[ValueProvider(NativeCodeGenRequest, generator)])

These are internal extension points. ``code_tools/x86_64_assembler.py`` encodes
instructions and tracks control flow; ``code_tools/x86_64_compiler.py`` lowers
object operations and manages owned references. Neither imports morphing,
providers or retorts. The x86 generator injects converter descriptions and the
recursive callable wrapper through its compiler factory. The CPython callable,
its constants and executable-memory lifetime live in
``code_tools/native_callable.py``.

``code_tools/x86_64_dictionary.py`` emits dictionary hash probes, ordered field
rows and ASCII key comparisons. It receives the compiler instance explicitly;
``X86Compiler`` delegates these operations while retaining the shared assembler
and reference ownership state.

An ARM implementation can consume the same plans and scalar descriptions
through ``NativeCodeGenerator.compile``. It still needs its own lowering,
stack layout, ABI and executable-memory support, including instruction-cache
synchronization. The shared plans describe conversion configuration, not a
portable instruction set; passing an ARM assembler to ``X86Compiler`` does
not port the x86 instructions.

Field IR and optimization
-------------------------

Flat native model loaders use a typed internal DSL defined in
``morphing/native/bytecodes.py``. ``model_ir.py`` translates resolved model plans into
field operations; ``optimizer.py`` rewrites them before the architecture
backend emits instructions. These modules do not import instruction emitters.
The current IR covers required field loading and the required prefix of models
with optional fields. Defaults, model construction and dumping retain their
existing lowering.

``ReadField`` produces an owned reference in source order. ``CheckType`` keeps
an exact-type value and preserves the original converter for other inputs.
``ConvertField`` replaces the value and marks a boundary that can execute
Python, mutate input or run finalizers when an input reference is released.
Conversion operations retain their original error paths.

``fuse_scalar_reads`` combines consecutive required reads and identity checks
into ``ReadScalarFields``. Its fast path requires verified exact-dictionary
keys and types. Failed guards execute the original operations in order, or the
existing whole-model fallback. A final raw read can join the batch while its
conversion remains after it; later reads never cross a conversion. Optional
reads stop fusion. Architecture and CPython-layout checks remain in lowering.

The compiled model program retains the optimized IR. Inlining reuses it while
allocating fresh machine-code slots for each occurrence. Adding another
architecture can reuse the same field operations and optimization rule;
register allocation, guards and reference handling still need backend lowering.

``bytecodes.py`` contains both instruction definitions and their bodies.
The bodies use the ``FieldBackend`` protocol for dictionary access, conditional
execution, converter calls and owned-reference replacement. ``FieldContext``
binds symbolic targets and replays original instructions on guard failures.
The x86 implementation in ``x86_64/fields.py`` emits branches and CPython calls;
the portable executor in tests runs the same bodies with Python values. The
operation semantics are shared, rather than reimplemented in a backend switch.
For native code, these bodies run during compilation. Calling the generated
loader executes machine code without interpreting field operations.
Model field calls also impose an inlining budget on child converters, including
containers. Reducing a child's code size below the compiler's general limit
must not cause a large body to be duplicated throughout its parent models.


Tools overview
================================

Venv managing
----------------

Bootstrap
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Initial preparation of venv and repo for developing.

.. code-block:: bash

    just bootstrap

Deps sync
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sync all dependencies. Need to run if committed dependencies are changed.

.. code-block:: bash

    just venv-sync

Compile dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compile raw dependencies (``requirements/raw/*``)
into file with locked versions via `uv pip compile <https://docs.astral.sh/uv/pip/compile/>`__.

.. code-block:: bash

    just deps-compile

This command try keep previous locked version. To upgrade locked dependencies use:

.. code-block:: bash

    just deps-compile-upgrade


Linting
----------------

Run linters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run all linters. Should be executed before tests.

.. code-block:: bash

    just lint


Testing
----------------

Run basic tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sequentially run basic tests on all python versions. It is useful to rapidly check that the code is working.

.. code-block:: bash

    just test

Run all tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parallelly run all tests on all python versions.

.. code-block:: bash

    just test-all

Run all tests (sequentially)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sequentially run all tests on all python versions. Failed parallel runs can have unclear output.

.. code-block:: bash

    just test-all-seq

Produce coverage report
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create coverage report. All coverage reports will be merged into ``coverage.xml`` file at working directory.
You can import it to IDE. Instruction for
`PyCharm <https://www.jetbrains.com/help/pycharm/switching-between-code-coverage-suites.html#add-remove-coverage-suite>`__.

.. code-block:: bash

    just cov


Documentation
----------------

Build documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate html files with documentation. Output files will be placed in ``docs-build/html``.

.. code-block:: bash

    just doc

Clean generated documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Clean generated documentation and build cache.
Sometimes sphinx can not detect changes in non-rst files.
This command fixes it.

.. code-block:: bash

    just doc-clean
