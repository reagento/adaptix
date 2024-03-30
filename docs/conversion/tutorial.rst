.. _conversion-tutorial:

***********
Tutorial
***********

Installation
=============

.. include:: /common/installation.rst

Introduction
====================

Building an easily maintainable application requires you to split the code into layers.
Data between layers should be passed using special data structures.
It requires creating many converter functions transforming one model into another.

Adaptix helps you avoid writing boilerplate code by generating conversion functions for you.

.. literalinclude:: /examples/conversion/tutorial/tldr.py

The actual signature of ``convert_book_to_dto`` is automatically derived by any type checker and any IDE.

Adaptix can transform between any of the supported models, see :ref:`supported-model-kinds`
for exact list of models and known limitations.

How it works? Adaptix scans each field of the destination model and matches it with the field of the source model.
By default, only fields with the same name are matched. You can :ref:`override <fields-linking>` this behavior.

Also, it works for nested models.

.. literalinclude:: /examples/conversion/tutorial/nested.py

Furthermore, there is :func:`.conversion.convert` that can directly convert one model to another,
but it is quite limited and can not configured, so it won't be considered onwards.

.. dropdown:: Usage of :func:`.conversion.convert`

  .. literalinclude:: /examples/conversion/tutorial/convert_function.py

Upcasting
=============

All source model additional fields not found in the destination model are simply ignored.

.. literalinclude:: /examples/conversion/tutorial/upcasting.py

Downcasting
=============

Sometimes you need to add extra data to the source model. For this, you can use a special decorator.

.. literalinclude:: /examples/conversion/tutorial/downcasting.py

:func:`.conversion.impl_converter` takes an empty function and generates its body by signature.

``# mypy: disable-error-code="empty-body"`` on the top of the file is needed
because mypy forbids functions without body.
Also, you can set this option at `mypy config <https://mypy.readthedocs.io/en/stable/config_file.html#example-mypy-ini>`_
or supress each error individually via ``# type: ignore[empty-body]``.

.. _fields-linking:

Fields linking
================

If the names of the fields are different, then you have to link them manually.

.. literalinclude:: /examples/conversion/tutorial/fields_linking.py

The first parameter of :func:`.conversion.link` is the predicate describing the field of the source model,
the second parameter is the pointing to the field of the destination model.

This notation means that the field ``author`` of class ``Book``
will be linked with the field ``writer`` of class ``BookDTO``.

You can use simple strings instead of ``P`` construct,
but it will match any field with the same name despite of owner class.

By default, additional parameters can replace fields only on the top-level model.
If you want to pass this data to a nested model, you should use :func:`.conversion.from_param` predicate factory.

.. literalinclude:: /examples/conversion/tutorial/nested_from_param.py

If the field name differs from the parameter name, you also can use :func:`.conversion.from_param` to link them.

Linking algorithm
===================

The building of the converter is based on a need to construct the destination model.

For each field of the destination model, adaptix searches a corresponding field.
Additional parameters are checked (from right to left) before the fields.
So, your custom linking looks among the additional parameters too.

By default, fields are matched by exact name equivalence,
parameters are matched only for top-level destination model fields.

After fields are matched adaptix tries to create a coercer
that transforms data from the source field to the destination type.

Type coercion
================

By default, there are no implicit coercions between scalar types.

However, there are cases where type casting involves passing the data as is and adaptix detects its:

- source type and destination type are the same
- destination type is ``Any``
- source type is a subclass of destination type (excluding generics)
- source union is a subset of destination union (simple ``==`` check is using)

Also, some compound types can be coerced if corresponding inner types are coercible:

- source and destination types are models (conversion like top-level models)
- source and destination types are ``Optional``
- source and destination types are one of the builtin iterable
- source and destination types are ``dict``


You can define your own coercion rule.

.. literalinclude:: /examples/conversion/tutorial/type_coercion.py

The first parameter of :func:`.conversion.coercer` is the predicate describing the field of the source model,
the second parameter is the pointing to the field of the destination model,
the third parameter is the function that casts source data to the destination type.

Usually, only field types are used as predicates here.

Also you can set coercer for specific linking via :paramref:`.conversion.link.coercer` parameter.

.. literalinclude:: /examples/conversion/tutorial/type_coercion_via_link.py

This coercer will have higher priority than defined via :func:`.conversion.coercer` function.


Putting together
===================

Let's explore complex example collecting all features together.

.. literalinclude:: /examples/conversion/tutorial/putting_together.py
