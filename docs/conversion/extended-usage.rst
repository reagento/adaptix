==================
Extended usage
==================

This section continues the tutorial to illuminate some more complex topics.

.. _link_function:

Link function
========================

Using :func:`.conversion.link_function` you can write your own functions
that will retrieve the necessary data directly from the model.

Link model
------------------------

Let's start with example of code.

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
