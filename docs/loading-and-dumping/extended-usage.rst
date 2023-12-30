==================
Extended usage
==================

This section continues the tutorial to illuminate some more complex topics.

Generic classes
========================

Generic classes are supported out of the box.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/generic_classes_simple.py

If a generic class is not parametrized, Python specification requires to assume ``Any`` for each position.
Adaptix acts slightly differently,
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

But it does not work with cyclic-referenced objects like

.. code-block:: python

   item_category.sub_categories.append(item_category)


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

There are more complex and more powerful use cases of ``map``, which will be described further.

Name style
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes JSON keys are quite normal but do fit PEP8 recommendations of variable naming.
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

On loading
^^^^^^^^^^^^^

Parameter :paramref:`.name_mapping.extra_in` controls policy how extra data is saved.

.. _on-loading-extra-skip:

:obj:`.ExtraSkip`
"""""""""""""""""""""""

Default behaviour. All extra data is ignored.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_skip.py

.. _on-loading-extra-forbid:

:obj:`.ExtraForbid`
"""""""""""""""""""""""

This policy raises :class:`.load_error.ExtraFieldsError` in case of any unknown field is found.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_extra_forbid.py

Order of fields inside :class:`.load_error.ExtraFieldsError` is not guaranteed and can be unstable between runs.

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
Precise type hint is ``Callable[[T, Mapping[str, Any]], None]``).
This callable can mutate the model to inject unknown data as you want.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_loading_saturator.py

On dumping
^^^^^^^^^^^^^

Parameter :paramref:`.name_mapping.extra_in` controls policy how extra data is extracted.

.. _on-dumping-extra-skip:

:obj:`.ExtraSkip`
"""""""""""""""""""""""

Default behaviour. All extra data is ignored.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_extra_skip.py

You can skip ``extra`` from dumping. See :ref:`fields-filtering` for detail.

.. _on-dumping-field-id:

Field id
""""""""""""""

You can pass the string with field name.
Dumper of this field must return a mapping that will be merged with dict of dumped representation.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_field_id.py

Output mapping keys have not collide with keys of dumped model. Otherwise the result is not guaranteed.

You can pass several field ids (``Iterable[str]``). The output mapping will be merged.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_several_field_id.py

Priority of output mapping is not guaranteed.

.. _on-dumping-extractor-function:

Extractor function
""""""""""""""""""""""

There is way to take out extra data from via custom function called 'extractor'.
A callable must taking model and produce mapping of extra fields.
Precise type hint is ``Callable[[T], Mapping[str, Any]]``).

.. literalinclude:: /examples/loading-and-dumping/extended_usage/unknown_fields_processing/on_dumping_extractor.py

Output mapping keys have not collide with keys of dumped model. Otherwise the result is not guaranteed.

Mapping to list
-----------------------------------

Some APIs store structures as lists or arrays rather than dict for optimization purposes.
For example, Binance uses it to represent
`historical market data <https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data>`_.

There is :paramref:`.name_mapping.as_list` that converts the model to a list.
Position at the list is determined by order of field definition.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list.py

You can override the order of fields using :paramref:`.name_mapping.map` parameter.

.. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list_map.py

Also, you can map the model to list via :paramref:`.name_mapping.map` without using :paramref:`.name_mapping.as_list`,
if you assign every field to their position on the list.

.. dropdown:: Mapping to list using only ``map``

   .. literalinclude:: /examples/loading-and-dumping/extended_usage/mapping_to_list_only_map.py


Structure flattening
------------------------------------

Custom mapping function
------------------------------------

Inheritance
-----------------------------------

Chaining (partial overriding)
-----------------------------------
