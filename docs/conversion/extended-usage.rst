==================
Extended usage
==================

This section continues the tutorial to illuminate some more complex topics.

.. _link_function:

Link function
========================

Using :func:`.conversion.link_function` you can write your functions
that will retrieve the necessary data directly from the model.

Link model
------------------------

Let's start with an example of code.

.. literalinclude:: /examples/conversion/extended_usage/link_function_model.py

The first argument of function receives a model instance. The function has to return the value of the field.

The input and output types are not checked, because there is no runtime tool to ensure that types are compatible.

Using converter extra parameters
----------------------------------

Additional parameters of the function are matched with additional parameters of the converter.

.. literalinclude:: /examples/conversion/extended_usage/link_function_with_extra_parameters.py

After linking, a default coercing mechanism is applied.

.. dropdown:: Example with coercing

  .. literalinclude:: /examples/conversion/extended_usage/link_function_with_extra_parameters_type_coercion.py

Merging several fields
---------------------------

You can get fields from the model, but it requires manual type casting.
All keyword-only are linked to the model field followed by common type coercing policies.

.. literalinclude:: /examples/conversion/extended_usage/link_function_fields.py

If the first parameter is keyword-only, it will be matched with the model field.


Link constant
========================

You can use :func:`.conversion.link_constant` to pass a constant value to the field.

.. literalinclude:: /examples/conversion/extended_usage/link_constant.py

To pass mutable objects you can use ``factory`` parameter. It takes callable accepting zero arguments.


Using default value for fields
================================

By default, all fields of the destination model must be linked to something
even field is not required (has a default value).

You can control this policy
via :func:`.conversion.allow_unlinked_optional` and :func:`.conversion.forbid_unlinked_optional`.

.. literalinclude:: /examples/conversion/extended_usage/using_default_value_for_fields.py

Each parameter of these functions are predicate defining the target scope of the policy.
You can use them without arguments to apply new policies to all fields.


What is a recipe really?
==============================

The recipe is the main concept of adaptix configuration.
It consists of objects defining (or redefining) some piece of behavior.
Each of these objects is called a `provider`.

Recipe system implements `chain-of-responsibility <https://en.wikipedia.org/wiki/Chain-of-responsibility_pattern>`__
design pattern.

Let's consider the case of creating linking for the destination field.
Firstly, adaptix filter providers that can create linking.
Secondly, adaptix scans the remaining recipe and applies the predicates of each provider.
The first match will be used, so begging providers overlap subsequent ones.


Eliminating recipe duplication via ``ConversionRetort``
==========================================================

Object holding recipe is called ``retort``.
You can use :class:`.conversion.ConversionRetort`
that exposes all high-level converting functions as methods
(``convert``, ``get_converter`` and ``impl_converter``).

.. literalinclude:: /examples/conversion/extended_usage/retort_introduction.py

This allows reusing your configuration recipe.
Parameter ``recipe`` of ``get_converter`` and ``impl_converter`` methods
inserts new providers into the beginning of the recipe, so you can override previously defined behavior.

No changes can be made after the retort creation. You can only make a new retort object based on the existing one.

Using ``.extend`` method you can add items to the recipe beginning.

.. literalinclude:: /examples/conversion/extended_usage/retort_extend.py
