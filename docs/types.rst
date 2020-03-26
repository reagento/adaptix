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
| Serializing       | x         | x         |                      |
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

Generic classes
========================

Generic classes supported out of the box. The difference is that if no schema found for concrete class, it will be taken for generic.

.. literalinclude:: examples/generic.py

.. note::
    Always pass concrete type as as second argument of ``dump`` method.
    Otherwise it will be treated as generic due to type erasure.

Polymorphic parsing
========================
