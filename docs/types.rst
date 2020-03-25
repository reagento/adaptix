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

Init-based parsing
========================

Generic classes
========================

Typed dict
=============

Dataclasses
===============

Polymorphic parsing
========================
