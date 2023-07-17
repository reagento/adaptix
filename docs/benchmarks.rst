==================
Benchmarks
==================


Measure principles
==============================================

These benchmarks aim to make a complete, fair, and reliable comparison
between different libraries among different versions of Python.

If you find a mistake in benchmarking methods or you want to add another library to the comparison
create a new `issue <https://github.com/reagento/dataclass-factory/issues>`__.

All benchmarks are made via `pyperf <https://github.com/psf/pyperf>`__ --
an advanced library used to measure the performance of Python interpreters.
It takes care of calibration, warming up, and gauging.

To handle a vast number of benchmarks variations and make pyperf API more convenient
new internal framework was created. It adds no overhead and is intended only to orchestrate ``pyperf`` runs.

All measurements exclude the time required to initialize and generate the conversion function.

Each library is tested with different options that `may` affect performance.

All benchmarks listed below were produced with libraries:

.. custom-bench-used-distributions::


Benchmarks analysis
==============================================

.. important::

  Serializing and deserializing libraries have a lot of options that customize the conversion process.
  These parameters may greatly affect performance
  but there is no way to create benchmarks for each combination of these options.
  So, performance for your specific case may be different.


.. _simple-structures-loading:

Simple Structures (loading)
-------------------------------

This benchmark examines the loading of basic structures natively supported by all the libraries.

The library has to produce models from dict:

.. literalinclude:: examples/benchmarks/simple_structures_models.py


.. custom-bench-chart:: simple_structures-loading


:octicon:`mark-github` :adaptix-view-repo-commit:`Source Code <benchmarks/benchmarks/simple_structures/hub_loading.py>`
:octicon:`file-zip` :adaptix-repo-commit:`Raw data <benchmarks/release_data/simple_structures-loading.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dp`` expresses that ``debug_path`` option of ``Retort`` is turned on
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
:octicon:`file-zip` :adaptix-repo-commit:`Raw data <benchmarks/release_data/simple_structures-dumping.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dp`` expresses that ``debug_path`` option of ``Retort`` is turned on
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
:octicon:`file-zip` :adaptix-repo-commit:`Raw data <benchmarks/release_data/gh_issues-loading.zip>`


.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dp`` expresses that ``debug_path`` option of ``Retort`` is turned on
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
:octicon:`file-zip` :adaptix-repo-commit:`Raw data <benchmarks/release_data/gh_dumping-loading.zip>`

.. centered:: Cases description

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: adaptix

        ``dp`` expresses that ``debug_path`` option of ``Retort`` is turned on
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

* **mashumaro** can not skip ``None`` values for specific fields out of the box.
  ``__post_serialize__`` is used to eliminate these fields.
