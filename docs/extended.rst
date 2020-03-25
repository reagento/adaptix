.. _extended_usage:

****************************
Extended usage
****************************

You can configure factory during its creation. You cannot change settings later it because they affect parsers which are crated only once for each instance of factory.

Most of configuration is done via Schemas. You can set default schema or one per type::

    factory = Factory(default_schema=Schema(...), schemas={ClassA: Schema(...)})


More verbose errors
=======================

Currently errors are not very verbose. But you can make them a bit better using ``debug_path`` of factory.
It is disabled by default because affects perfomance.

It this mode ``InvalidFieldError`` is thrown when some dataclass field cannot be parsed.
It contains ``field_path`` which is path to the field in provided data (key and indexes).


Working with field names
==========================

Name mapping
**********************

In some cases you have json with keys which are called not very good. For example, they contain spaces or just have unclear meaning.
Simplest way to fix it is to set custom name mapping. You can call fields as you want and factory will translate them using your mappind

.. literalinclude:: examples/name_mapping.py

Fields absent in mapping are not translated and used with their original names (meaning original is dataclass specification).


Stripping underscore
**********************

It is not often necessary to fill name mapping. One of the most common case is dictionary keys which are python keywords.
For example, you cannot use string ``from`` as a field name, but it very likely to sse in APIs. Usually it is solved by adding trailing underscore (e.g. ``from_``).

Dataclass factory will trim trailing underscores so you won't really meet this case.

.. literalinclude:: examples/trailing_.py

Sometimes this behavior is unwanted, so you can disable this feature by setting ``trim_trailing_underscore=False`` in Schema (in default schema of concrete one).
Also you can re-enable it for certain types

.. literalinclude:: examples/trailing_keep.py


Name styles
**********************

Sometimes json keys are quite normal, but ugly. For example they are named using CamelCase, but PEP8 recommends you to use snake_case.
Of cause, you can prepare name mapping, but it is too much to write for such stupid thing.

Dataclass factory can translate such names automatically. You need to declare fields as recommended by PEP8 (e.g. *field_name*) and set corresponding ``name_style``.
As usual, if no style is set for certain type, it will be taken from default schema.

By the way, you cannot convert names that do not follow snake_case style. In this case the only valid style is ``ignore``


.. literalinclude:: examples/name_style.py

Following name styles are supported:

* ``snake`` (snake_case)
* ``kebab`` (kebab-case)
* ``camel_lower`` (camelCaseLower)
* ``camel`` (CamelCase)
* ``lower`` (lowercase)
* ``upper`` (UPPERCASE)
* ``upper_snake`` (UPPER_SNAKE_CASE)
* ``camel_snake`` (Camel_Snake)
* ``dot`` (dot.case)
* ``camel_dot`` (Camel.Dot)
* ``upper_dot`` (UPPER.DOT)
* ``ignore`` (not real style, but just does no conversion)


Selecting and skipping fields
==================================

You have several ways to skip processing of some fields.

**Important**: Skipped fields MUST NOT be required in class constructor, otherwise parsing will fail

Only and exclude
*******************

If you know exactly what fields must be parsed/serialized and want to ignore all others just set them as ``only`` parameter of schema.
Also you can provide a list with excluded names via ``exclude``.

It affects both parsing and serializing

.. literalinclude:: examples/only_exc.py

Skip Internal
****************

More simplified case is to skip so called *internal use* fields, those fields which name starts with underscore.
You can skip them from parsing and serialization using ``skip_internal`` option of schema

It is disabled by default. It affects both parsing and serializing

.. literalinclude:: examples/skip_internal.py

Omit default
****************

If you have defaults for some fields, it is not really necessary to store them it serialized representation. For example this may be ``None``, empty list or something else.
You can omit them when serializing using ``omit_default`` option. Thos values thar are **equal** to default, will be stripped from resulting dict.

It is disabled by default. It affect only serialising.

.. literalinclude:: examples/omit_default.py

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
