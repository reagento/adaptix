.. _benchmarks:

==================
Benchmarks
==================


Measure principles
==============================================

These benchmarks aim to make a complete, fair, and reliable comparison
between different libraries among different versions of Python.

If you find a mistake in benchmarking methods or you want to add another library to the comparison
create a new `issue <https://github.com/reagento/adaptix/issues>`__.

All benchmarks are made via `pyperf <https://github.com/psf/pyperf>`__ --
an advanced library used to measure the performance of Python interpreters.
It takes care of calibration, warming up, and gauging.

To handle a vast number of benchmarks variations and make pyperf API more convenient
new internal framework was created. It adds no overhead and is intended only to orchestrate ``pyperf`` runs.

Unless explicitly labelled as fresh-converter or process-startup cases,
measurements exclude the time required to initialize and generate the conversion function.

Each library is tested with different options that `may` affect performance.

The four charts below were rerun on October 11, 2026, on Linux x86-64 (WSL2)
with an AMD Ryzen 9 9950X, using CPython 3.13.15 and 3.14.4.
All libraries and configurations were measured again on the same machine;
results from earlier hardware are not mixed into these charts.
Each case uses six pyperf worker processes, five measured values per worker,
two warmup values, a minimum value duration of 50 ms, and affinity to CPU 2.
Cases failing the stability checks (including a 4% relative standard deviation
limit) are remeasured with ten worker processes, eight values per worker and a minimum value duration
of 100 ms (200 ms for marshmallow dumping on CPython 3.14).
Error bars show the standard deviation of the measured values
(30 normally, 80 in these longer runs).
Marshmallow's Simple Structures dumping case on CPython 3.14 retains a 5.0%
relative standard deviation after the longer runs, primarily between worker
processes. All worker values are retained and its error bar shows this variation.
The other 168 cases pass the stability checks.

These charts measure conversion between Python dictionaries/lists and model objects.
They do not measure JSON parsing or encoding, nor converter generation.
The raw archives and their provenance are versioned in ``benchmarks/published_data``
alongside the benchmark definitions, so documentation builds use data from the same checkout.
Both Adaptix backends use the same dataclasses, recipes, coercion settings and
``DebugTrail`` modes. The ``python`` tag selects ``CodeGenBackend.PYTHON``;
``x86_64`` selects ``CodeGenBackend.X86_64``. Native cases are skipped on
unsupported interpreters and platforms.

Native loading cases and their msgspec comparisons on both interpreters were
remeasured after adding scalar field batches, direct optional-key probes and
bounded model inlining. CPython 3.13 also uses direct construction of ordinary
model instances. Models with custom initialization continue to execute their
Python initializer.

To reproduce the published scenarios after installing ``requirements/bench.txt``,
run the following on each interpreter::

    for module in simple_structures.hub_loading simple_structures.hub_dumping \
                  gh_issues.hub_loading gh_issues.hub_dumping; do
        python -m benchmarks.$module run \
            --pyperf-arg=--affinity=2 \
            --pyperf-arg=--processes=6 --pyperf-arg=--values=5 \
            --pyperf-arg=--warmups=2 --pyperf-arg=--min-time=0.05
    done

Choose an available CPU for ``--affinity`` on your machine.
Results are saved by the existing benchmark framework; ``run --missing`` resumes
an interrupted run, and ``run --unstable`` reruns missing or unstable cases.
To rebuild the release archives after running both tox benchmark environments::

    python -m benchmarks.bench_nexus release \
        --include simple_structures-loading simple_structures-dumping gh_issues-loading gh_issues-dumping \
        --env-include py313 py314

On CPython 3.14, dataclass-factory 2.16 cannot generate converters for the
GitHub Issues models. Its two loading variants and dumping variant are omitted
on that interpreter; they are measured on CPython 3.13. No timing is assigned
to an unsupported case.

The ``simple_structures-codegen`` benchmark compares the Python and experimental x86-64
code generation backends using identical models and conversion settings. It measures
both loading and dumping of a single ``Review`` (``flat``) and a ``Book`` containing
100 reviews (``nested``), with each ``DebugTrail`` mode and strict coercion enabled.
Additional ``DebugTrail.ALL`` cases load reviews with fresh string-key objects
(``nested_fresh_keys``), load and dump slotted models (``nested_slots``), and dump
alternating review subclasses (``nested_polymorphic``). These exercise cache misses and
different object layouts as well as repeated accesses to a single model type.
The ``nested_diverse`` case also creates a separate title and rating for every review,
exercising reference transfers for dynamically allocated scalar values.
The x86-64 cases are skipped on unsupported interpreters and platforms.

Run this comparison on the current interpreter after installing Adaptix and
the benchmark requirements::

    python -m benchmarks.simple_structures.hub_codegen run --storage-type fs --fs-data-dir .cache/codegen-benchmarks
    python -m benchmarks.simple_structures.hub_codegen check --storage-type fs --fs-data-dir .cache/codegen-benchmarks

The hub is also available through ``bench_nexus run --include simple_structures-codegen``.
Raw pyperf measurements and backend settings are saved for every case.

The ``simple_structures-competitors`` hub compares both backends with Pydantic,
msgspec, cattrs, mashumaro, dataclass-factory, Marshmallow, and Schematics using
the same ``Book`` with 100 reviews and the same ``content`` to ``text`` alias.
It reuses the existing library benchmarks, including strict and permissive
loading, detailed validation, and msgspec's optional ``gc=False`` models.
Adaptix loading uses strict coercion and all three ``DebugTrail`` settings.
Each library uses its own model representation and validation rules.
Measurements cover conversion between Python dictionaries and model objects;
JSON encoding and decoding are excluded. Pydantic dumping uses
``model_dump(mode="json", by_alias=True)`` to produce a Python dictionary.

Run the comparison after installing ``requirements/bench.txt``::

    python -m benchmarks.simple_structures.hub_competitors run --storage-type fs --fs-data-dir .cache/competitor-benchmarks
    python -m benchmarks.simple_structures.hub_competitors check --storage-type fs --fs-data-dir .cache/competitor-benchmarks

The hub is also available through ``bench_nexus run --include simple_structures-competitors``.

The ``backend-matrix`` hub compares the experimental x86-64 backend with msgspec
across scalar values, models with required or defaulted fields, wide models,
books with 0, 1, or 100 reviews, integer lists, dictionaries, nullable values,
enums, datetimes, nested lists, and the existing GitHub Issues snapshot.
Loading uses strict validation and ``DebugTrail.ALL``. Model cases also include
msgspec's ``gc=False`` option. Both loading and dumping are checked against the
expected values before measuring. msgspec loading calls ``convert`` directly
with its default ``strict=True``; no Python wrapper is timed.

Models use dataclasses for Adaptix and Structs for msgspec. These measurements
cover Python objects rather than JSON. Results from the Book workload alone
do not establish which library is faster for other schemas or data sizes.

Run this comparison with the benchmark requirements installed::

    python -m benchmarks.hub_backend_matrix run --storage-type fs --fs-data-dir .cache/backend-matrix
    python -m benchmarks.hub_backend_matrix check --storage-type fs --fs-data-dir .cache/backend-matrix

The ``backend-stress`` hub extends this comparison to other container sizes,
Unicode, date/time and timezone-aware datetime, bytes, UUID, Decimal, tuples and
sets, slotted and frozen models, default factories, post-init callbacks,
recursive models, tagged unions, and models with 128 fields.
Invalid inputs include an error at the beginning or end of a list and many
errors at once. Adaptix's ``DebugTrail.ALL`` collects errors, whereas
``DebugTrail.FIRST`` and msgspec stop at the first error; both Adaptix modes are
measured and reported separately.

JSON cases compare typed msgspec decoding/encoding with an Adaptix pipeline
using either generic msgspec JSON or the Python standard library JSON module.
These include parsing/encoding and use the same JSON values. Fresh-converter
cases create a new Retort or msgspec Decoder on each call with model classes
already defined. Process-startup cases include starting Python, importing the
library, defining a four-field model, and performing its first conversion.
These different operations must be interpreted separately from warm object
conversion timings::

    python -m benchmarks.hub_backend_stress run --storage-type fs --fs-data-dir .cache/backend-stress
    python -m benchmarks.hub_backend_stress check --storage-type fs --fs-data-dir .cache/backend-stress

The ``backend-types`` hub combines primitive and nullable types, scalar and
container unions, literals, enums, bytes, Decimal, UUID and date/time types with
lists, variable and fixed tuples, dictionaries, nested containers, and model
fields. Models include both dataclass-versus-Struct and dataclass-versus-dataclass
comparisons. Additional cases cover empty and small containers, non-list input
iterables, container subclasses, sets, dictionary keys, and TypedDict.
The hub includes comparisons where both libraries support the input and produce
equivalent results. Primitive result types are checked explicitly: equality of
``1``, ``1.0`` and ``True`` does not make their conversions equivalent::

    python -m benchmarks.hub_backend_types run --storage-type fs --fs-data-dir .cache/backend-types

A broader audit also includes all matrix and stress cases, public Retort API
calls, error modes, JSON, fresh converters and process startup. It records every
attempt, including unsupported inputs and differences in semantics::

    python -m benchmarks.audit_backend --output .cache/backend-audit/results.json --processes 3 --gc on

This audit uses short, calibrated timings to find candidates for further pyperf
measurement. It marks an advantage only if it exceeds 10 percent in every worker
process; other results are recorded as close or noisy. Run with ``--gc off`` to
check the effect of garbage collection, or ``--validate-only --processes 1`` to
check results without timing. Use ``--filter`` to select a substring of case names.
Add ``--scalar-unions`` to enumerate all unions of two or more types from
``int``, ``str``, ``bool``, ``float`` and ``None``, including each scalar branch
and integer inputs converted by float branches.
For example, ``--scalar-unions --filter scalar_union_`` selects cases whose names
contain ``scalar_union_``.
Warm cases exclude converter construction. Error modes, JSON and startup are
separate operations and do not establish the speed of warm object conversion.
No finite matrix proves that a library is faster for every possible schema,
input distribution, recipe or environment.

All benchmarks listed below were produced with libraries:

.. custom-bench-used-distributions::


Benchmarks analysis
==============================================

.. important::

  Serializing and deserializing libraries have a lot of options that customize the conversion process.
  These parameters may greatly affect performance
  but there is no way to create benchmarks for each combination of these options.
  So, performance for your specific case may be different.


The table summarizes ``DebugTrail.ALL`` for both Adaptix backends, strict
loading for Adaptix and msgspec, and GC-enabled msgspec models. Times are
means in microseconds; the charts below retain every configuration and its
standard deviation. The last column is Python-backend time divided by
x86-64-backend time.

.. csv-table:: Published warm conversion results
    :header: "CPython", "Scenario", "Adaptix Python (μs)", "Adaptix x86-64 (μs)", "msgspec (μs)", "Speedup vs Python"
    :widths: 8, 20, 19, 19, 16, 18

    "3.13", "Simple loading", "20.91", "2.93", "4.40", "7.13x"
    "3.13", "Simple dumping", "8.58", "2.55", "4.26", "3.36x"
    "3.13", "GitHub loading", "119.05", "17.02", "24.50", "6.99x"
    "3.13", "GitHub dumping", "73.67", "17.81", "29.36", "4.14x"
    "3.14", "Simple loading", "23.82", "2.92", "4.42", "8.17x"
    "3.14", "Simple dumping", "9.03", "1.85", "4.12", "4.88x"
    "3.14", "GitHub loading", "128.53", "16.89", "24.52", "7.61x"
    "3.14", "GitHub dumping", "76.40", "13.53", "26.99", "5.65x"

.. _simple-structures-loading:

Simple Structures (loading)
-------------------------------

This benchmark examines the loading of basic structures natively supported by all the libraries.

The library has to produce models from dict:

.. literalinclude:: examples/benchmarks/simple_structures_models.py


.. custom-bench-chart:: simple_structures-loading


:octicon:`mark-github` :adaptix-view-repo-commit:`Source Code <benchmarks/benchmarks/simple_structures/hub_loading.py>`
:octicon:`file-zip` :download:`Raw data <../benchmarks/published_data/simple_structures-loading.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dt_all``, ``dt_first`` and ``dt_disable`` expresses that ``debug_trail`` parameter of ``Retort``
        set to ``DebugTrail.ALL``, ``DebugTrail.FIRST``, ``DebugTrail.DISABLE``
        (:ref:`doc <retort-configuration>`)

        ``sc`` refers to that ``strict_coercion`` option of ``Retort`` is activated
        (:ref:`doc <retort-configuration>`)

    .. grid-item-card:: msgspec

        ``strict`` implies that parameter ``strict`` at ``convert`` is enabled
        (`doc <https://jcristharif.com/msgspec/api.html#msgspec.convert>`__)

        ``no_gc`` points to that models have disabled ``gc`` option
        (`doc <https://jcristharif.com/msgspec/structs.html#disabling-garbage-collection-advanced>`__)

    .. grid-item-card:: cattrs

        ``dv`` indicates that ``Converter`` option ``detailed_validation`` is enabled
        (`doc <https://catt.rs/en/stable/validation.html#detailed-validation>`__)

    .. grid-item-card:: dataclass_factory

        ``dp`` denotes that parameter ``debug_path`` of ``Factory`` is set to ``True``
        (`doc <https://dataclass-factory.readthedocs.io/en/latest/extended.html#more-verbose-errors>`__)

    .. grid-item-card:: mashumaro

        ``lc`` signifies that ``lazy_compilation`` flag of model ``Config`` is activated
        (`doc <https://github.com/Fatal1ty/mashumaro#lazy_compilation-config-option>`__)

    .. grid-item-card:: pydantic

        ``strict`` means that parameter ``strict`` at ``model_config`` is turned on
        (`doc <https://docs.pydantic.dev/latest/usage/strict_mode/#strict-mode-with-configdict>`__)


Notes about implementation:

* **marshmallow** can not create an instance of dataclass or another model, so, ``@post_load`` hook was used
  (`doc <https://marshmallow.readthedocs.io/en/stable/extending.html#pre-processing-and-post-processing-methods>`__)

* **msgspec** can not be built for pypy

|


.. _simple-structures-dumping:

Simple Structures (dumping)
-------------------------------

This benchmark studies the dumping of basic structures natively supported by all the libraries.

The library has to convert the model instance to dict used at loading benchmark:

.. literalinclude:: examples/benchmarks/simple_structures_models.py

.. custom-bench-chart:: simple_structures-dumping

:octicon:`mark-github` :adaptix-view-repo-commit:`Source Code <benchmarks/benchmarks/simple_structures/hub_dumping.py>`
:octicon:`file-zip` :download:`Raw data <../benchmarks/published_data/simple_structures-dumping.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dt_all``, ``dt_first`` and ``dt_disable`` expresses that ``debug_trail`` parameter of ``Retort``
        set to ``DebugTrail.ALL``, ``DebugTrail.FIRST``, ``DebugTrail.DISABLE``
        (:ref:`doc <retort-configuration>`)

    .. grid-item-card:: msgspec

        ``no_gc`` points to that models have disabled ``gc`` option
        (`doc <https://jcristharif.com/msgspec/structs.html#disabling-garbage-collection-advanced>`__)

    .. grid-item-card:: cattrs

        ``dv`` indicates that ``Converter`` option ``detailed_validation`` is enabled
        (`doc <https://catt.rs/en/stable/validation.html#detailed-validation>`__)

    .. grid-item-card:: mashumaro

        ``lc`` signifies that ``lazy_compilation`` flag of model ``Config`` is activated
        (`doc <https://github.com/Fatal1ty/mashumaro#lazy_compilation-config-option>`__)

    .. grid-item-card:: pydantic

        ``strict`` means that parameter ``strict`` at ``model_config`` is turned on
        (`doc <https://docs.pydantic.dev/latest/usage/strict_mode/#strict-mode-with-configdict>`__)

    .. grid-item-card:: asdict

        standard library function :external+python:py:func:`dataclasses.asdict` was used


Notes about implementation:

* **asdict** does not support renaming, produced dict contains the original field name

* **msgspec** can not be built for pypy

* **pydantic** requires using ``json`` mode of ``model_dump`` method
  to produce json serializable dict
  (`doc <https://docs.pydantic.dev/latest/usage/serialization/#modelmodel_dump>`__)

|

.. _github-issues-loading:

GitHub Issues (loading)
------------------------

This benchmark examines libraries using real-world examples.
It involves handling a slice of a CPython repository issues snapshot fetched via the
`GitHub REST API <https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues>`__.

The library has to produce models from dict:

.. dropdown:: Processed models

  The original endpoint returns an array of objects. Some libraries have no sane way to process a list of models,
  so root level list wrapped with ``GetRepoIssuesResponse`` model.

  These models represent most of the fields returned by the endpoint,
  but some data are skipped.
  For example, ``milestone`` is missed out, because the CPython repo does not use it.

  .. literalinclude:: examples/benchmarks/gh_issues_models.py


.. custom-bench-chart:: gh_issues-loading

:octicon:`mark-github` :adaptix-view-repo-commit:`Source Code <benchmarks/benchmarks/gh_issues/hub_loading.py>`
:octicon:`file-zip` :download:`Raw data <../benchmarks/published_data/gh_issues-loading.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dt_all``, ``dt_first`` and ``dt_disable`` expresses that ``debug_trail`` parameter of ``Retort``
        set to ``DebugTrail.ALL``, ``DebugTrail.FIRST``, ``DebugTrail.DISABLE``
        (:ref:`doc <retort-configuration>`)

        ``sc`` refers to that ``strict_coercion`` option of ``Retort`` is activated
        (:ref:`doc <retort-configuration>`)

    .. grid-item-card:: msgspec

        ``strict`` implies that parameter ``strict`` at ``convert`` is enabled
        (`doc <https://jcristharif.com/msgspec/api.html#msgspec.convert>`__)

        ``no_gc`` points to that models have disabled ``gc`` option
        (`doc <https://jcristharif.com/msgspec/structs.html#disabling-garbage-collection-advanced>`__)

    .. grid-item-card:: cattrs

        ``dv`` indicates that ``Converter`` option ``detailed_validation`` is enabled
        (`doc <https://catt.rs/en/stable/validation.html#detailed-validation>`__)

    .. grid-item-card:: dataclass_factory

        ``dp`` denotes that parameter ``debug_path`` of ``Factory`` is set to ``True``
        (`doc <https://dataclass-factory.readthedocs.io/en/latest/extended.html#more-verbose-errors>`__)

    .. grid-item-card:: mashumaro

        ``lc`` signifies that ``lazy_compilation`` flag of model ``Config`` is activated
        (`doc <https://github.com/Fatal1ty/mashumaro#lazy_compilation-config-option>`__)


Notes about implementation:

* **marshmallow** can not create an instance of dataclass or another model, so, ``@post_load`` hook was used
  (`doc <https://marshmallow.readthedocs.io/en/stable/extending.html#pre-processing-and-post-processing-methods>`__)

* **msgspec** can not be built for pypy

* **pydantic** strict mode accepts only enum instances for the enum field, so, it cannot be used at this benchmark
  (`doc <https://docs.pydantic.dev/latest/usage/conversion_table/>`__)

* **cattrs** can not process datetime out of the box.
  Custom structure hook ``lambda v, tp: datetime.fromisoformat(v)`` was used.
  This function does not generate a descriptive error, therefore production implementation could be slower.

|

.. _github-issues-dumping:

GitHub Issues (dumping)
------------------------

This benchmark examines libraries using real-world examples.
It involves handling a slice of a CPython repository issues snapshot fetched via the
`GitHub REST API <https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues>`__.

The library has to convert the model instance to dict used at loading benchmark:

.. dropdown:: Processed models

  The original endpoint returns an array of objects. Some libraries have no sane way to process a list of models,
  so root level list wrapped with ``GetRepoIssuesResponse`` model.

  These models represent most of the fields returned by the endpoint,
  but some data are skipped.
  For example, ``milestone`` is missed out, because the CPython repo does not use it.

  GitHub API distinct nullable fields and optional fields.
  So, default values must be omitted at dumping,
  but fields with type ``Optional[T]`` without default must always be presented

  .. literalinclude:: examples/benchmarks/gh_issues_models.py


.. custom-bench-chart:: gh_issues-dumping

:octicon:`mark-github` :adaptix-view-repo-commit:`Source Code <benchmarks/benchmarks/gh_issues/hub_dumping.py>`
:octicon:`file-zip` :download:`Raw data <../benchmarks/published_data/gh_issues-dumping.zip>`

.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dt_all``, ``dt_first`` and ``dt_disable`` expresses that ``debug_trail`` parameter of ``Retort``
        set to ``DebugTrail.ALL``, ``DebugTrail.FIRST``, ``DebugTrail.DISABLE``
        (:ref:`doc <retort-configuration>`)

    .. grid-item-card:: msgspec

        ``no_gc`` points to that models have disabled ``gc`` option
        (`doc <https://jcristharif.com/msgspec/structs.html#disabling-garbage-collection-advanced>`__)

    .. grid-item-card:: cattrs

        ``dv`` indicates that ``Converter`` option ``detailed_validation`` is enabled
        (`doc <https://catt.rs/en/stable/validation.html#detailed-validation>`__)

    .. grid-item-card:: mashumaro

        ``lc`` signifies that ``lazy_compilation`` flag of model ``Config`` is activated
        (`doc <https://github.com/Fatal1ty/mashumaro#lazy_compilation-config-option>`__)

    .. grid-item-card:: pydantic

        ``strict`` means that parameter ``strict`` at ``model_config`` is turned on
        (`doc <https://docs.pydantic.dev/latest/usage/strict_mode/#strict-mode-with-configdict>`__)

    .. grid-item-card:: asdict

        standard library function :external+python:py:func:`dataclasses.asdict` was used


Notes about implementation:

* **asdict** does not support renaming, produced dict contains the original field name

* **msgspec** can not be built for pypy

* **pydantic** requires using ``json`` mode of ``model_dump`` method
  to produce json serializable dict
  (`doc <https://docs.pydantic.dev/latest/usage/serialization/#modelmodel_dump>`__)

* **cattrs** can not process datetime out of the box.
  Custom unstructure hook ``datetime.isoformat`` was used.

* **marshmallow** can not skip ``None`` values for specific fields out of the box.
  ``@post_dump`` is used to remove these fields.
