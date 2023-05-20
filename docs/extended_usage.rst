==================
Extended usage
==================

This section continues the tutorial to illuminate some more complex topics.

Generic classes
========================

Generic classes are supported out of the box.

.. literalinclude:: examples/extended_usage/generic_classes_simple.py

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
   * - ``A = TypeVar('A', str, bytes)``
     - ``Union[str, bytes]``


You should always pass concrete type to the second argument :meth:`.Retort.dump` method.
There is no way to determine the type parameter of an object at runtime due to type erasure.
So, the taken data will be treated as a non-parametrized generic.


Recursive data types
========================

These types could be loaded and dumped without additional configuration.

.. literalinclude:: examples/extended_usage/recursive_data_types.py

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

.. literalinclude:: examples/extended_usage/mutating_field_name.py

The keys of ``map`` refers to the field name at model definition,
and values contain a new field name.

Fields absent in ``map`` are not translated and used with their original names.

There are more complex and more powerful use cases of ``map``, which will be described further.

Name style
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes JSON keys are quite normal but do fit PEP8 recommendations of variable naming.
You can rename each field individually, but library can automatically translate such names.

.. literalinclude:: examples/extended_usage/name_style.py

See :class:`.NameStyle` for a list of all available target styles.

You cannot convert names that do not follow snake_case style.
:paramref:`.name_mapping.map` takes precedence over :paramref:`.name_mapping.name_style`,
so you can use it to rename fields that do not follow snake_case or override automatic style adjusting.

Stripping underscore
^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes API uses reserved Python keywords therefore it can not be used as a field name.
Usually, it is solved by adding a trailing underscore to the field name (e.g. ``from_`` or ``import_``).
Retort trims trailing underscore automatically.

.. literalinclude:: examples/extended_usage/stripping_underscore.py

If this behavior is unwanted, you can disable this feature by setting ``trim_trailing_underscore=False``

.. literalinclude:: examples/extended_usage/stripping_underscore_disable.py

:paramref:`.name_mapping.map` is prioritized over :paramref:`.name_mapping.trim_trailing_underscore`.


Fields filtering
-----------------------------------

You can select which fields will be loaded or dumped.
Two parameters that can be used for these: :paramref:`.name_mapping.skip` and :paramref:`.name_mapping.only`

.. literalinclude:: examples/extended_usage/fields_filtering_skip.py

Excluding the required field makes it impossible to create a loader, but the dumper will work properly.

.. dropdown:: Same example but with using ``only``

   .. literalinclude:: examples/extended_usage/fields_filtering_only.py

.. dropdown:: Skipping optional field

   .. literalinclude:: examples/extended_usage/fields_filtering_skip_optional.py
      :lines: 2-

Both parameters take predicate or iterable of predicates, so you can use all features of :ref:`predicate-system`.
For example, you can filter fields based on their type.

.. literalinclude:: examples/extended_usage/fields_filtering_type.py
   :lines: 2-


Omit default
-----------------------------------

If you have defaults for some fields, it could be unnecessary to store them in dumped representation.
You can omit them when serializing a :paramref:`.name_mapping.omit_default` parameter.
Values that are equal to default, will be stripped from the resulting dict.

.. literalinclude:: examples/extended_usage/omit_default.py

By default, ``omit_default`` is disabled, you can set it to ``True`` which will affect all fields.
Also, you can pass any predicate or iterable of predicate to apply the rule only to selected fields.

.. literalinclude:: examples/extended_usage/omit_default_selective.py


Unknown fields processing
-----------------------------------

By default, all extra data that is absent in the target structure are ignored.
You can change this behavior via :paramref:`.name_mapping.extra_in` and :paramref:`.name_mapping.extra_out` parameters.

Possible values for :paramref:`.name_mapping.extra_in`:

#. :obj:`.ExtraSkip` -- all extra data is ignored
#. :obj:`.ExtraForbid` -- :class:`.load_error.ExtraFieldsError` is raised in case of any unknown field is found
#. :obj:`.ExtraKwargs` -- extra data are passed as additional keyword arguments.
#. Field id (``str``) -- loader of the specified field will receive all unknown data.
#. Several field ids (``Iterable[str]``) -- same as the previous one, but each field loader will receive
#. ``Saturator`` (``Callable[[T, Mapping[str, Any]], None]``) --
   a callable taking created model and mapping of unknown data.
   This callable can mutate the model to inject unknown data as you want.

Possible values for :paramref:`.name_mapping.extra_out`:

#. :obj:`.ExtraSkip` -- extra data is not extracting
#. Field id (``str``) -- model will be passed to the dumper, it has to produce mapping with extra data that will be merged with dict of other fields.
#. Several field ids (``Iterable[str]``) --
#. ``Extractor`` (``Callable[[T], Mapping[str, Any]]``) --


Mapping to list
-----------------------------------

Some APIs store structures as lists or arrays rather than dict for optimization purposes.
For example, Binance uses it to represent
`historical market data <https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data>`_.

There is :paramref:`.name_mapping.as_list` that converts the model to a list.
Position at the list is determined by order of field definition.

.. literalinclude:: examples/extended_usage/mapping_to_list.py

You can override the order of fields using :paramref:`.name_mapping.map` parameter.

.. literalinclude:: examples/extended_usage/mapping_to_list_map.py

Also, you can map the model to list via :paramref:`.name_mapping.map` without using :paramref:`.name_mapping.as_list`,
if you assign every field to their position on the list.

.. dropdown:: Mapping to list using only ``map``

   .. literalinclude:: examples/extended_usage/mapping_to_list_only_map.py


Structure flattening
------------------------------------

Custom mapping function
------------------------------------

Inheritance
-----------------------------------

Chaining (partial overriding)
-----------------------------------
