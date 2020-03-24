.. _extended_usage:

****************************
Extended usage
****************************

You can configure factory during its creation. You cannot change settings later it because they affect parsers which are crated only once for each instance of factory.

Most of configuration is done via Schemas. You can set default schema or one per type::

    factory = Factory(default_schema=Schema(...), schemas={ClassA: Schema(...)})


More verbose errors
========================

Currently pa

Name mapping
========================

Name styles
========================

Custom parsers and serializers
========================

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
