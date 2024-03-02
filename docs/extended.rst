.. include:: new_major_version.rst

.. _extended_usage:

****************************
Extended usage
****************************

You can configure the factory during its creation. You can't change the settings later because they affect parsers, which are created only once for each instance of a factory.

Most of the configuration is done via Schemas. You can set default schema or one per type::

    factory = Factory(default_schema=Schema(...), schemas={ClassA: Schema(...)})


More verbose errors
=======================

Currently, errors are not very verbose. But you can make them a bit better using ``debug_path`` of a factory.
It is disabled by default because affects performance.

In this mode ``InvalidFieldError`` is thrown when some dataclass field cannot be parsed.
It contains ``field_path`` which is a path to the field in provided data (key and indexes).


Working with field names
==========================

Name mapping
**********************

In some cases, you have json with keys that leave much to be desired. For example, they might contain spaces or just have unclear meanings.
The simplest way to fix it is to set a custom name mapping. You can call fields as you want and the factory will translate them using your mapping.

.. literalinclude:: examples/name_mapping.py

Fields absent in mapping are not translated and used with their original names (as in dataclass specification).


Stripping underscore
**********************

It is often unnecessary to fill name mapping. One of the most common cases is dictionary keys which are python keywords.
For example, you cannot use the string ``from`` as a field name, but it is very likely to see in APIs. Usually, it is solved by adding a trailing underscore (e.g. ``from_``).

Dataclass factory will trim trailing underscores so you won't meet this case.

.. literalinclude:: examples/trailing_.py

Sometimes this behavior is unwanted, so you can disable this feature by setting ``trim_trailing_underscore=False`` in Schema (in default schema of the concrete one).
Also, you can re-enable it for certain types.

.. literalinclude:: examples/trailing_keep.py


Name styles
**********************

Sometimes json keys are quite normal but ugly. For example, they are named using CamelCase, but PEP8 recommends you to use snake_case.
Of cause, you can prepare name mapping, but it is too much to write for such a stupid thing.

The library can translate such names automatically. You need to declare fields as recommended by PEP8 (e.g. *field_name*) and set corresponding ``name_style``.
As usual, if no style is set for a certain type, it will be taken from the default schema.

By the way, you cannot convert names that do not follow snake_case style. In this case, the only valid style is ``ignore``


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

.. note::
    Skipped fields MUST NOT be required in class constructor, otherwise parsing will fail

Only and exclude
*******************

If you know exactly what fields must be parsed/serialized and want to ignore all others just set them as ``only`` parameter of schema.
Also, you can provide a list with excluded names via ``exclude``.

It affects both parsing and serializing.

.. literalinclude:: examples/only_exc.py

Only mapped
*************

Already have ``name_mapping`` and do not want to repeat all names in ``only`` parameter? Just set ``only_mapped=True``. It will ignore all fields which are not described in name mapping.

Skip Internal
****************

More simplified case is to skip so-called *internal use* fields, those fields which name starts with underscore.
You can skip them from parsing and serialization using ``skip_internal`` option of schema.

It is disabled by default. It affects both parsing and serializing.

.. literalinclude:: examples/skip_internal.py

Omit default
****************

If you have defaults for some fields, it is unnecessary to store them in serialized representation. For example, this may be ``None``, empty list or something else.
You can omit them when serializing using ``omit_default`` option. Those values that are **equal** to default, will be stripped from the resulting dict.

It is disabled by default. It affects only serialising.

.. literalinclude:: examples/omit_default.py

Structure flattening
========================

Another case of ugly API is a too complex hierarchy of data. You can fix it using already known ``name_mapping``.
Earlier, you used it to rename fields, but also you can use it to map a name to a nested value by specifying a path to it.

Integers in the path are treated as list indices, strings - as dict keys.
It affects parsing and serializing.

For example, you have an author of a book with only field - name (see :ref:`nested`). You can expand this dict and store the author name directly in your Book class.

.. literalinclude:: examples/flatten.py

We can modify example above to store author as a list with name

.. literalinclude:: examples/flatten_list.py

Automatic naming during flattening
***************************************

If names somewhere in "complex" structure are the same, as in your class you can simplify your schema using ellipsis (``...``).
There are two simple rules:

* ``...`` as as a key in ``name_mapping`` means `Any` field. Path will be applied to every field that is not declared explicitly in mapping
* ``...`` inside path in ``name_mapping`` means that original name of field will be reused. If name style or other rules are provided the will be applied to the name.

Examples:

.. literalinclude:: examples/flatten_auto.py

Parsing unknown fields
===========================

By default, all extra fields that are absent in the target structure are ignored. But this behavior is not necessary.
For now, you can select from several variants setting ``unknown`` attribute of Schema

* ``Unknown.SKIP`` - default behavior. All unknown fields are ignored (skipped)
* ``Unknown.FORBID`` - ``UnknownFieldsError`` is raised in case of any unknown field is found
* ``Unknown.STORE`` - all unknown fields passed unparsed to the constructor of a class.
  Your ``__init__`` must be ready for this
* Field name (``str``). The specified field is filled with all unknowns and the parser of the corresponding type is called.
  For simple cases, you can annotate that field with ``Dict`` type.
  In the case of serialization, this field is also serialized and the result is merged up with the current result.
* Several field names (sequence of ``str``). The behavior is very similar to the case with one field name.
  All unknowns are collected to a single dict and it is passed to parsers of each provided field (be careful modifying data at ``pre_parse`` step).
  Also, their dump results are merged when serializing


.. literalinclude:: examples/unknown_fields.py

Additional steps
========================

Most of the work is done automatically, but you may want to do some additional processing.

Real parsing process has following flow::

   ╔══════╗      ┌───────────┐      ┌────────┐      ┌────────────┐      ╔════════╗
   ║ data ║ ---> │ pre_parse │ ---> │ parser │ ---> │ post_parse │ ---> ║ result ║
   ╚══════╝      └───────────┘      └────────┘      └────────────┘      ╚════════╝

The same is for serializing::

   ╔══════╗      ┌───────────────┐      ┌────────────┐      ┌────────────────┐      ╔════════╗
   ║ data ║ ---> │ pre_serialize │ ---> │ serializer │ ---> │ post_serialize │ ---> ║ result ║
   ╚══════╝      └───────────────┘      └────────────┘      └────────────────┘      ╚════════╝

So the return value of ``pre_parse`` is passed to ``parser``, and return value of ``post_parse`` is used as the total result of the parsing process.
You can add your logic at any step, but mind the main difference:

* ``pre_parse`` and ``post_serialize`` work with serialized representation of data (e.g. dict for dataclasses)
* ``post_parse`` and ``pre_serialize`` work with instances of your classes.

So if you want to do some validation - it is better to do at ``post_parse`` step.
And if you want to do *polymorphic parsing* - check if a type is suitable before parsing is started at ``pre_parse``.

Another case is to change the representation of some fields: serialize json to string, split values and so on.

.. literalinclude:: examples/pre_post.py


Schema inheritance
========================

In some cases, it might be useful to subclass Schema instead of just creating instances normally.

.. literalinclude:: examples/subclass.py

.. note::
    In versions <2.9: Factory created a copy of a schema for each type filling in missed args.
    If you need to get access to some data in schema, get a working instance of the schema with ``Factory.schema`` method

.. note::
    Single schema instance can be used multiple time simultaneously because of multithreading or recursive structures.
    Be careful modifying data in the schema


Json-schema
==========================

You can generate json schema for your classes.

Note that factory does it lazily and caches the result. So, if you need definitions for all of your classes, create schema for each top-level class using the ``json_schema`` method
and then collect all definitions using ``json_schema_definitions``

.. literalinclude:: examples/jsonschema.py

Result of ``json_schema`` call is

.. literalinclude:: examples/jsonschema_res.json

Result of ``json_schema_definitions`` call is

.. literalinclude:: examples/jsonschema_defs.json

.. note::
    Not all features of dataclass factory are supported currently. You cannot generate json-schema if you use structure-flattening, additional parsing of unknown fields or init-based parsing.
    Also, if you have custom parsers or pre-parse step, schema might be incorrect.
