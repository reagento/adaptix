==================
Extended usage
==================

This section continues the tutorial to illuminate some more complex topics.

Native x86-64 code generation
==============================

``Retort`` can generate executable x86-64 machine code for model loaders and dumpers::

    from dataclasses import dataclass

    from adaptix import CodeGenBackend, Retort

    @dataclass
    class Book:
        title: str
        pages: int

    retort = Retort(codegen_backend=CodeGenBackend.X86_64)
    book = retort.load({"title": "Example", "pages": 120}, Book)
    assert retort.dump(book) == {"title": "Example", "pages": 120}

The backend requires Linux x86-64 and a GIL-enabled CPython build.
It needs no external assembler, C compiler, or additional Python dependency.
Unsupported platforms raise ``RuntimeError`` when configuring the retort.
``CodeGenBackend.PYTHON`` is the default on every platform.
Use ``retort.replace(codegen_backend=...)`` to switch backends while preserving the recipe.

CPython structure offsets are described separately for each supported version in
``adaptix._internal.code_tools.cpython_layout``. These files are generated from
the interpreter's headers using ``offsetof`` and ``sizeof``. Runtime checks
validate the layouts before enabling direct memory access. Unknown versions,
prereleases and incompatible builds keep the C API path.

To regenerate a layout, run the development script with the matching interpreter::

    python3.15 scripts/generate_cpython_layout.py \
        --output src/adaptix/_internal/code_tools/cpython_layout/v3_15.py

The script needs a C compiler and CPython development headers; they are only
needed when updating the layout files.

The native backend lowers model shapes and name layouts directly to machine code.
It does not generate or compile Python source for the model functions.
The generated code uses the
`CPython C API <https://docs.python.org/3/c-api/call.html>`_
to call converters, build containers, and invoke constructors.
Recognized CPython 3.13–3.15 release builds also use guarded caches to read
instance attributes, object slots, and entries in ordinary string-key dictionaries
directly. Type versions, storage validity, and key identities or short ASCII
key contents are checked before each access. Cache training is bounded for
polymorphic workloads; unsupported layouts use the ordinary attribute or item getter.
Exact-type checks for standard strict ``int``, ``str``, ``bool``, and ``float``
loaders are emitted directly when the interpreter's object layout is recognized.
Exact lists use a native traversal loop with reserved output storage. Scalar,
nullable, enum, datetime, nested-list and eligible model conversions can be emitted
inside their containing program. Lists of unchanged scalar values use a compact
checking and copying loop. The loop preserves Python list iteration rules when a converter mutates
the input, and collects diagnostic information only on failure.
On recognized CPython 3.13–3.15 builds, scalar dictionaries can copy the existing
table and validate its values without calling a Python converter for each entry.
Canonical naive ISO datetimes have native parsing and formatting paths; other ISO
spellings, timezone handling and subclasses use the standard converter.
On recognized CPython 3.14–3.15 release builds, plain initializers consisting entirely
of field assignments can also be replaced by guarded allocation and field stores.
Custom constructors, setters, tracing, and changed initializer code use the ordinary
constructor path. The guards are checked again after allocation, which can run GC.
Eligible models with omitted default fields avoid intermediate argument containers;
the loader preserves the defaults selected by the input shape. Wide models can use
guarded dictionary storage for construction and batched attribute reads.
Other conversions and custom recipe converters use their normal callables.
Shared Python helpers implement layout policies and exception handling.
Nested models, recursive models, dict/list layouts, defaults, omitted fields,
extra-data policies, and all ``DebugTrail`` modes are supported.

This backend is experimental and is not a performance guarantee.
Measure loading and dumping with your own models before choosing it for performance.
The repository's ``simple_structures/codegen`` benchmark compares both backends
on flat and nested models in every ``DebugTrail`` mode.
Reference-count operations are inlined for recognized CPython 3.10–3.15 release builds;
other builds use the C API. Diagnostic state is allocated only when needed on the
optimized paths. Recognized CPython 3.14–3.15 builds can create output dictionaries
with a shared key table and a compact value buffer, transferring converted values
directly into their final storage. CPython 3.13 and larger dictionaries copy a
validated key template. Both paths preserve dictionary behavior and GC tracking;
other builds use the C API to build dictionaries.
Generated functions use at most 64 KiB of native stack space;
models requiring a larger frame raise ``ValueError`` during generation.

Executable allocations are held by the generated callable, so it remains usable
after its retort is released. Code memory is writable during generation and
read-only/executable afterwards.
Internal code-generation hooks receive an Intel-syntax assembly listing in
``CodeGenHookData.source``, the executable bytes in ``machine_code``,
and ``CodeGenBackend.X86_64`` in ``backend``.

Generic classes
========================

Generic classes are supported out of the box.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/generic_classes_simple.py

If a generic class is not parametrized, Python specification requires to assume ``Any`` for each position.
|adaptix| acts slightly differently,
it derives implicit parameters based on ``TypeVar`` properties.

.. list-table::
   :header-rows: 1

   * - TypeVar
     - Derived implicit parameter
   * - ``T = TypeVar('T')``
     - ``Any``
   * - ``B = TypeVar('B', bound=Book)``
     - ``Book``
   * - ``C = TypeVar('C', str, bytes)``
     - ``Union[str, bytes]``


You should always pass concrete type to the second argument :meth:`.Retort.dump` method.
There is no way to determine the type parameter of an object at runtime due to type erasure.
If you pass non-parametrized generic, retort will raise error.


Recursive data types
========================

These types could be loaded and dumped without additional configuration.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/recursive_data_types.py
   :lines: 2-

But it does not work with cyclic-referenced objects like

.. code-block:: python

   item_category.sub_categories.append(item_category)


Dealing with ``if TYPE_CHECKING``
===================================

.. include:: /common/dealing-with-if-type-checking.rst


.. _detecting-absence-of-a-field:


Detecting absence of a field
=====================================

Sometimes you need to detect that user does not pass any value to the field.
You can use None for this, but that makes it impossible to distinguish from a user-provided value.

To solve this, you can use special types called "sentinels".
Since they cannot be represented in the outside world,
they provide a reliable way to determine when a field value was not explicitly set by the user.

``Omitted`` is the builtin sentinel type. Let's examine how it can be used:

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/omitted.py
   :lines: 1-18

Enabling ``omit_default`` policy is required here. It allow to skip this value at dumping.
All missing fields are filled by default value (``Omitted``), and this fields are omitted at dumping.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/omitted.py
   :lines: 20-27

``None`` value is accepted as usual for None-able fields:

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/omitted.py
   :lines: 29-36

But ``None`` value is forbidden for fields without ``None`` type:

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/omitted.py
   :lines: 38-44


Also, you can create own sentinel types via :func:`.as_sentinel`.

.. dropdown:: Custom sentinel type

  .. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/custom_sentinel.py


If ``None`` is invalid value for every field, you can treat ``None`` as sentinel.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/none_as_sentinel.py
   :lines: 1-20


.. dropdown:: Test examples

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/none_as_sentinel.py
      :lines: 23-38


You can also use ``NotRequired`` fields of ``TypedDict`` for this,
but ``TypedDict`` itself is quite limited compared to other models.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/detecting_absense_of_a_field/typed_dict.py


Name mapping
========================

The name mapping mechanism allows precise control outer representation of a model.

It is configured entirely via :func:`.name_mapping`.

The first argument of this function is a predicate,
which selects affected classes (see :ref:`predicate-system` for detail).
If it is omitted, rules will be applied to all models.


Mutating field name
------------------------

There are several ways to change the name of a field for loading and dumping.

Field renaming
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes you have JSON with keys that leave much to be desired.
For example, they might be invalid Python identifiers or just have unclear meanings.
The simplest way to fix it is to use :paramref:`.name_mapping.map` to rename it.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/field_renaming.py

The keys of ``map`` refers to the field name at model definition,
and values contain a new field name.

Fields absent in ``map`` are not translated and used with their original names.

There are more complex and more powerful use cases of ``map``, which will be described at :ref:`advanced-mapping`.

Name style
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes JSON keys are quite normal but do not fit PEP8 recommendations of variable naming.
You can rename each field individually, but library can automatically translate such names.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/name_style.py

See :class:`.NameStyle` for a list of all available target styles.

You cannot convert names that do not follow snake_case style.
:paramref:`.name_mapping.map` takes precedence over :paramref:`.name_mapping.name_style`,
so you can use it to rename fields that do not follow snake_case or override automatic style adjusting.

Stripping underscore
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes API uses reserved Python keywords therefore it can not be used as a field name.
Usually, it is solved by adding a trailing underscore to the field name (e.g. ``from_`` or ``import_``).
Retort trims trailing underscore automatically.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/stripping_underscore.py

If this behavior is unwanted, you can disable this feature by setting ``trim_trailing_underscore=False``

.. literalinclude:: /examples/loading-and-dumping/extended_usage/stripping_underscore_disable.py

:paramref:`.name_mapping.map` is prioritized over :paramref:`.name_mapping.trim_trailing_underscore`.

.. _fields-filtering:

Fields filtering
-----------------------------------

You can select which fields will be loaded or dumped.
Two parameters that can be used for these: :paramref:`.name_mapping.skip` and :paramref:`.name_mapping.only`

.. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_skip.py

.. dropdown:: Traceback of raised error

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_skip.pytb

Excluding the required field makes it impossible to create a loader, but the dumper will work properly.

.. dropdown:: Same example but with using ``only``

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_only.py

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_only.pytb


.. dropdown:: Skipping optional field

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_skip_optional.py
      :lines: 2-

Both parameters take predicate or iterable of predicates, so you can use all features of :ref:`predicate-system`.
For example, you can filter fields based on their type.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/fields_filtering_type.py
   :lines: 2-


Omit default
-----------------------------------

If you have defaults for some fields, it could be unnecessary to store them in dumped representation.
You can omit them when serializing a :paramref:`.name_mapping.omit_default` parameter.
Values that are equal to default, will be stripped from the resulting dict.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/omit_default.py

By default, ``omit_default`` is disabled, you can set it to ``True`` which will affect all fields.
Also, you can pass any predicate or iterable of predicate to apply the rule only to selected fields.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/omit_default_selective.py


Unknown fields processing
-----------------------------------

Unknown fields are the keys of mapping that do not map to any known field.

By default, all extra data that is absent in the target structure are ignored.
You can change this behavior via :paramref:`.name_mapping.extra_in` and :paramref:`.name_mapping.extra_out` parameters.

Field renaming does not affect on unknown fields, collected unknown fields will have original names.

On loading
^^^^^^^^^^^^^

Parameter :paramref:`.name_mapping.extra_in` controls policy how extra data is saved.

.. _on-loading-extra-skip:

:obj:`.ExtraSkip`
"""""""""""""""""""""""

Default behavior. All extra data is ignored.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_skip.py

.. _on-loading-extra-forbid:

:obj:`.ExtraForbid`
"""""""""""""""""""""""

This policy raises :class:`.load_error.ExtraFieldsLoadError` in case of any unknown field is found.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_forbid.py

.. custom-non-guaranteed-behavior::

  Order of fields inside :class:`.load_error.ExtraFieldsLoadError` is not guaranteed and can be unstable between runs.

.. _on-loading-extra-kwargs:

:obj:`.ExtraKwargs`
"""""""""""""""""""""""

Extra data are passed as additional keyword arguments.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_kwargs.py

This policy has significant flaws by design and, generally, should not be used.

All extra fields are passed as additional keywords arguments without any conversion,
specified type of ``**kwargs`` is ignored.

If an unknown field collides with the original field name,
``TypeError`` will be raised, treated as an unexpected error.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_kwargs_renaming.py

The following strategy one has no such problems.

.. _on-loading-field-id:

Field id
""""""""""""""

You can pass the string with field name. Loader of corresponding field will receive mapping with unknown data.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_field_id.py

Also you can pass ``Iterable[str]``. Each field loader will receive same mapping of unknown data.

.. _on-loading-saturator-function:

Saturator function
""""""""""""""""""""""

There is a way to use a custom mechanism of unknown field saving.

You can pass a callable taking created model and mapping of unknown data named 'saturator'.
Precise type hint is ``Callable[[T, Mapping[str, Any]], None]``.
This callable can mutate the model to inject unknown data as you want.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_saturator.py

On dumping
^^^^^^^^^^^^^

Parameter :paramref:`.name_mapping.extra_in` controls policy how extra data is extracted.

.. _on-dumping-extra-skip:

:obj:`.ExtraSkip`
"""""""""""""""""""""""

Default behavior. All extra data is ignored.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_extra_skip.py

You can skip ``extra`` from dumping. See :ref:`fields-filtering` for detail.

.. _on-dumping-field-id:

Field id
""""""""""""""

You can pass the string with field name.
Dumper of this field must return a mapping that will be merged with dict of dumped representation.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_field_id.py

.. custom-non-guaranteed-behavior::

  Output mapping keys have not collide with keys of dumped model. Otherwise the result is not guaranteed.

You can pass several field ids (``Iterable[str]``). The output mapping will be merged.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_several_field_id.py

.. custom-non-guaranteed-behavior::

  Priority of output mapping is not guaranteed.

.. _on-dumping-extractor-function:

Extractor function
""""""""""""""""""""""

There is way to take out extra data from via custom function called 'extractor'.
A callable must taking model and produce mapping of extra fields.
Precise type hint is ``Callable[[T], Mapping[str, Any]]``.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_extractor.py

.. custom-non-guaranteed-behavior::

  Output mapping keys have not collide with keys of dumped model. Otherwise the result is not guaranteed.

Mapping to list
-----------------------------------

Some APIs store structures as lists or arrays rather than dict for optimization purposes.
For example, Binance uses it to represent
`historical market data <https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data>`__.

There is :paramref:`.name_mapping.as_list` that converts the model to a list.
Position at the list is determined by order of field definition.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list.py

You can override the order of fields using :paramref:`.name_mapping.map` parameter.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list_map.py

Also, you can map the model to list via :paramref:`.name_mapping.map` without using :paramref:`.name_mapping.as_list`,
if you assign every field to their position on the list.

.. dropdown:: Mapping to list using only ``map``

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list_only_map.py

Only :obj:`.ExtraSkip` and :obj:`.ExtraForbid` is could be used with mapping to list.

.. _structure-flattening:

Structure flattening
------------------------------------

Too complex hierarchy of structures in API could be fixed via ``map`` parameter.
Earlier, you used it to rename fields,
but also you can use it to map a name to a nested value by specifying a path to it.
Integers in the path are treated as list indices, strings - as dict keys.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/structure_flattening.py

This snippet could be reduced.

1) Ellipsis (``...``) inside path is replaced by original field name after automatic conversions.
2) Dict could be replaced with a list of pairs.
   The first item of the pair is predicate (see :ref:`predicate-system` for detail),
   the second is the mapping result (path in this case).

.. literalinclude:: /examples/loading-and-dumping/extended_usage/structure_flattening_compressed.py


Chaining (partial overriding)
-----------------------------------

Result ``name_mapping`` is computed by merging all parameters of matched ``name_mapping``.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/chaining.py

The first provider override parameters of next providers.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/chaining_overriding.py


.. _private_fields_dumping:

Private fields dumping
-----------------------------------

By default, |adaptix| skips private fields (any field starting with underscore) at dumping.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/private_fields_skipping_pydantic.py

You can include this fields by setting alias.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/private_fields_including_pydantic.py

Alias can be equal to field name (field id) and field will be included.

.. dropdown:: Including private field without renaming

    .. literalinclude:: /examples/loading-and-dumping/extended_usage/private_fields_including_no_rename_pydantic.py


.. _advanced-mapping:

Advanced mapping
---------------------------------------

Let's figure it out with all features of :paramref:`.name_mapping.map`.

:paramref:`.name_mapping.map` can take data in two forms:

1) :external+python:py:class:`collections.abc.Mapping` with keys of field ids and values with mapping result
2) Iterable of pairs (tuple of two elements) or providers or mapping described above.
   Provider interface for mapping currently is unstable and would not be described at this article.
   If you pass a tuple of two elements,
   the first item must be predicate (see :ref:`predicate-system` for detail),
   and the second item must be mapping result or function returning mapping result.

If you use mapping all keys must be ``field_id`` (e.g. valid python identifiers),
so regexes like ``a|b`` is not allowed.

The mapping result is union of 5 types:

1) String of external field name
2) Integer indicating index inside output sequence
3) Ellipsis (``...``) that will be replaced with the key
   after builtin conversions by :paramref:`.name_mapping.trim_trailing_underscore`, :paramref:`.name_mapping.name_style`
   and :paramref:`.name_mapping.as_list`.
4) Iterable of string, integer or ellipsis, aka :ref:`structure-flattening`
5) ``None`` that means skipped field.
   :paramref:`.name_mapping.map` is applied after :paramref:`.name_mapping.only`.
   So the field will be skipped despite the match by :paramref:`.name_mapping.only`.

Name mapping reuses concepts of recipe inside retort and also implements
`chain-of-responsibility <https://en.wikipedia.org/wiki/Chain-of-responsibility_pattern>`__ design pattern.

Only the first element matched by its predicate is used to determine the mapping result.

The callable producing mapping result must take two parameters: the shape of the model and the field.
Types of these parameters currently are internal.
You can find an exact definition in the source code but it could change in the future.

Example of using advanced techniques:

.. literalinclude:: /examples/loading-and-dumping/extended_usage/advanced_mapping.py

Some XML APIs or APIs derived from XML do not use plural forms for repeated fields.
So you need to strip the plural form at external representation.

The first item of :paramref:`.name_mapping.map` is dict that renames individual field.
The second item is a tuple created by a function.
The function constructs appropriate regex to match fields and trim plural suffixes.

The merging of ``map`` is different from other parameters. A new ``map`` does not replace others.
The new iterable is concatenated to the previous.
