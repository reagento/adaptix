.. _extended_usage:

****************************
Extended usage
****************************

You can configure factory during its creation. You cannot change settings later it because they affect parsers which are crated only once for each instance of factory.

Most of configuration is done via Schemas. You can set default schema or one per type::

    factory = Factory(default_schema=Schema(...), schemas={ClassA: Schema(...)})


More verbose errors
========================

Currently errors are not very verbose. But you can make them a bit better using ``debug_path`` of factory.
It is disabled by default because affects perfomance.

It this mode ``InvalidFieldError`` is thrown when some dataclass field cannot be parsed.
It contains ``field_path`` which is path to the field in provided data (key and indexes).


Name mapping
========================

In some cases you have json with keys which are called not very good. For example, they contain spaces or just have unclear meaning.
Simplest way to fix it is to set custom name mapping. You can call fields as you want and factory will translate them using your mappind

.. literalinclude:: examples/name_mapping.py

Fields absent in mapping are not translated and used with their original names (meaning original is dataclass specification).

Name styles
========================

Custom parsers and serializers
================================

Additinal steps
========================

Polymorphic parsing
========================

Schema inheritance
========================

Generic classes
========================

Omit default
========================

Structure flattening
========================

Init-based parsing
========================
