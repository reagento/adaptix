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

   * CPython 3.9
   * CPython 3.10
   * CPython 3.11
   * CPython 3.12
   * CPython 3.13
   * PyPy 3.8
   * PyPy 3.9
   * PyPy 3.10

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
