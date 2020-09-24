***************************
Specific types behavior
***************************

Structures
===========

Out of the box dataclass factory supports three types of structures:

* dataclasses
* TypedDict (``total`` is also checked)
* other classes with annotated ``__init__``

+-------------------+-----------+-----------+----------------------+
| Feature           | dataclass | TypedDict | Class with __init__  |
+===================+===========+===========+======================+
| Parsing           | x         | x         | x                    |
+-------------------+-----------+-----------+----------------------+
| Name conversion   | x         | x         | x                    |
+-------------------+-----------+-----------+----------------------+
| Omit default      | x         |           |                      |
+-------------------+-----------+-----------+----------------------+
| Skip internal     | x         | x         |                      |
+-------------------+-----------+-----------+----------------------+
| Serializing       | x         | x         | x                    |
+-------------------+-----------+-----------+----------------------+

Custom parsers and serializers
================================

Not all types are supported out of the box. For example, it is unclear how to parse datetime: it can be represented as unixtime or iso format or something else.
If you meet unsupported type you can provide your own parser and serializer:

.. literalinclude:: examples/custom.py

Common schemas
==================

We have subpackage called ``dataclass_factory.schema_helpers`` with some common schemas:

* ``unixtime_schema`` - converts ``datetime`` to unixtime and vice versa
* ``isotime_schema`` - converts ``datetime`` to string containing ISO 8601. Supported only on Python 3.7+
* ``uuid_schema`` - converts ``UUID`` objects to string


Self referenced types
=======================

Just place correct annotations and use factory.

.. literalinclude:: examples/self_referenced.py

Generic classes
========================

Generic classes supported out of the box. The difference is that if no schema found for concrete class, it will be taken for generic.

.. literalinclude:: examples/generic.py

.. note::
    Always pass concrete type as as second argument of ``dump`` method.
    Otherwise it will be treated as generic due to type erasure.

Polymorphic parsing
========================

Very common case is to select class based on information in data.

If required fields differ between classes, no configuration required. But sometimes you want to make a selection more explicitly.
For example, if data field "type" equals to "item" data should be parsed as Item, if it is "group" then Group class should be used.

For such case you can use ``type_checker`` from ``schema_helpers`` module. It creates a function, which should be used on ``pre_parse`` step.
By default it checks ``type`` field of data, but you can change it

.. literalinclude:: examples/polymorphic.py

If you need you own pre_parse function, you can set it as parameter for ``type_checker`` factory.

For more complex cases you can write your own function.
Just raise ``ValueError`` if you detected that current class is not acceptable for provided data, and parser will go to the next one in ``Union``
