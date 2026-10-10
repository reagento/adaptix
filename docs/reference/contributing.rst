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
==================================

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
built-in implementation as a default dependency. Currently only
``X86CodeGenerator`` is implemented. It receives a ``compiler_factory`` and
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

An ARM implementation can consume the same plans and scalar descriptions
through ``NativeCodeGenerator.compile``. It still needs its own lowering,
stack layout, ABI and executable-memory support, including instruction-cache
synchronization. The shared plans describe conversion configuration, not a
portable instruction set; passing an ARM assembler to ``X86Compiler`` does
not port the x86 instructions.


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
