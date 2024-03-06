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
By default, only fields with the same name are matched. You can :ref:`override <field-linking>` this behavior.

Also, it works for nested models.

.. literalinclude:: /examples/conversion/tutorial/nested.py

Furthermore, there is :func:`.conversion.convert` that can directly convert one model to another,
but it is quite limited and can not configured, so it won't be considered onwards.

.. dropdown:: Usage of :func:`.conversion.convert`

  .. literalinclude:: /examples/conversion/tutorial/convert_function.py


Downcasting
=============

All source model additional fields not found in the destination model are simply ignored.

.. literalinclude:: /examples/conversion/tutorial/downcasting.py

Upcasting
=============

Sometimes you need to add extra data to the source model. For this, you can use a special decorator.

.. literalinclude:: /examples/conversion/tutorial/upcasting.py

:func:`.conversion.impl_converter` takes an empty function and generates its body by signature.

``# mypy: disable-error-code="empty-body"`` on the top of the file is needed
because mypy forbids functions without body.
Also, you can set this option at `mypy config <https://mypy.readthedocs.io/en/stable/config_file.html#example-mypy-ini>`_
or supress each error individually via ``# type: ignore[empty-body]``.

.. _field-linking:

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

Linking algorithm
===================

The building of the converter is based on a need to construct the destination model.

For each field of the destination model, adaptix searches a corresponding field.
Additional parameters are checked (from right to left) before the fields.
So, your custom linking looks among the additional parameters too.

By default, fields are matched by exact name equivalence.

After fields are matched adaptix tries to create a coercer
that transforms data from the source field to the destination type.

Type coercion
================

By default, there are no implicit coercions.

However, there are cases where type casting involves passing the data as is and adaptix detects its:

* source type and destination type are the same
* destination type is ``Any``
* source type is a subclass of destination type (excluding generics)
* source union is subset of destination union (simple ``==`` check is using)
* source type and destination type is ``Optional`` and inner types are coercible

You can define your own coercion rule.

.. literalinclude:: /examples/conversion/tutorial/type_coercion.py

The first parameter of :func:`.conversion.coercer` is the predicate describing the field of the source model,
the second parameter is the pointing to the field of the destination model,
the third parameter is the function that casts source data to the destination type.

Usually, only field types are used as predicates here.


Putting together
===================

Let's explore complex example collecting all features together.

.. literalinclude:: /examples/conversion/tutorial/putting_together.py
