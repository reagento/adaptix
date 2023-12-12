==================
Contributing
==================

How to setup the repository
================================

.. warning::
    All internal tools and scripts are designed only to work on Linux.
    You have to use WSL to develop the project on Windows.


1. Install `Just <https://github.com/casey/just?tab=readme-ov-file#packages>`_

   Just is a command runner that is used here instead of ``make``.

2. Install all needed python interpreters

   * CPython 3.8
   * CPython 3.9
   * CPython 3.10
   * CPython 3.11
   * CPython 3.12
   * PyPy 3.8
   * PyPy 3.9
   * PyPy 3.10

3. Clone repository with submodules

   .. code-block:: bash

      git clone --recurse-submodules https://github.com/reagento/dataclass-factory

4. Checkout to ``3.x/develop``

   .. code-block:: bash

      git switch 3.x/develop

   If you already cloned the project and forgot ``--recurse-submodules``,
   directory ``benchmarks/release_data`` will be empty.
   You can fix it executing ``git submodule update --init --recursive``.

5. Create `venv <https://docs.python.org/3/library/venv.html>`_ and run

   .. code-block:: bash

      just bootstrap

6. Run main commands to check that everything is ok

   .. code-block:: bash

      just lint
      just test-all-p


Tools overview
================================

Venv managing
----------------

.. code-block:: bash

    just bootstrap

Initial preparation venv and repo for developing.

.. code-block:: bash

    just venv-sync

Sync all dependencies. Need to run if committed dependencies are changed.

Linting
----------------

.. code-block:: bash

    just lint

Run all linters. Should be executed before tests.

Testing
----------------

.. code-block:: bash

    just test

Run basic tests on all python versions. It is useful to rapidly check that the code is working

.. code-block:: bash

    just test-all-p

Run all tests on all python versions parallelly.

.. code-block:: bash

    just test-all

Run all tests on all python versions. Failed parallel runs can have unclear output.

.. code-block:: bash

    just cov

Produce coverage report. All coverage reports will be merged into ``coverage.xml`` file at working directory.
You can import it to IDE. Instruction for
`PyCharm <https://www.jetbrains.com/help/pycharm/switching-between-code-coverage-suites.html#add-remove-coverage-suite>`_.

Documentation
----------------

.. code-block:: bash

    just doc

Build documentation.

.. code-block:: bash

    just doc-clean

Clean generated documentation and build cache.
Sometimes sphinx can not detect changes in non-rst files.
This command fixes it.
