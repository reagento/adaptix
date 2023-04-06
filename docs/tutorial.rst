***********
Tutorial
***********

Adaptix analyzes your type hints and generates corresponding converters based on the retrieved information.
You can flexibly tune the conversion process following DRY principle.

Installation
=============

Just use pip to install the library::

    pip install adaptix


Introduction
====================

The central object of the library is `Retort`.
It can create models from mapping (loading) and create mappings from the model (dumping).


.. literalinclude:: examples/tutorial/tldr.py


All typing information is retrieved from your annotations, so it is not required from you to provide any schema
or even change your dataclass decorators or class bases.

In provided example ``book.author == "Unknown author"`` because normal dataclass constructor is called.

It is better to create a retort only once because all loaders are cached inside it after the first usage.
Otherwise, the structure of your classes will be analyzed again and again for every new instance of Retort.


Nested objects
--------------------

Nested objects are supported out of the box. It is surprising,
but you do not have to do anything except define your dataclasses.
For example, you expect that author of the Book is an instance of a Person, but in the dumped form it is a dictionary.

Declare your dataclasses as usual and then just load your data.

.. literalinclude:: examples/tutorial/nested.py


Lists and other collections
--------------------------------

Want to load a collection of dataclasses?
No changes are required, just specify the correct target type (e.g ``List[SomeClass]`` or ``Dict[str, SomeClass]``).

.. literalinclude:: examples/tutorial/collection.py

Fields also can contain any supported collections.


Retort configuration
======================

There are two options that :class:`.Retort` constructor takes.

:paramref:`debug_path` parameter is responsible for saving path where exception was caused.
You can disable this option if data is loading or dumping from a trusted source where an error is unlikely.
It will slightly improve performance if no error will be caused and will have more impact if an exception will be raised.
More detail about working with the saved path in :ref:`Struct path`


:paramref:`strict_coercion` affects only the loading process.
If it is enabled (this is default state) type will be converted only two conditions passed:

#. There is only one way to produce casting
#. No information will be lost

So this mode forbids converting  ``dict`` to ``list`` (dict values will be lost),
forbids converting ``str`` to ``int`` (we do not know which base must be used),
but allows to converting ``str`` to ``Decimal`` (base always is 10 by definition).

Strict coercion requires additional type checks before calling the main constructor,
therefore disabling it can improve performance.

.. _retort-recipe:

Retort recipe
----------------
Retort also supports a more powerful and more flexible configuration system via `recipe`.
It implements `chain-of-responsibility <https://en.wikipedia.org/wiki/Chain-of-responsibility_pattern>`_
design pattern.
The recipe consists of `providers`, each of which can precisely override one of the retort's behavior aspects.

.. literalinclude:: examples/tutorial/retort_recipe_intro.py

Default ``datetime`` loader accepts only ``str`` in ``ISO 8601`` format,
``loader(datetime, datetime.fromtimestamp)`` replaces it with function ``datetime.fromtimestamp``
that takes ``int`` representing ``Unix time``.

.. dropdown:: Same example but with dumper

  .. literalinclude:: examples/tutorial/retort_recipe_intro_dumper.py

Providers at the start of the recipe have higher priority because they overlap subsequent ones.

.. literalinclude:: examples/tutorial/recipe_providers_priority.py

Basic providers overview
---------------------------

The list of providers is not limited to :func:`.loader` and :func:`.dumper`,
there are a lot of other high-level helpers. Here are some of them.

#. :func:`.constructor` creates a loader that extracts data from dict and passes it to the given function.
#. :func:`.name_mapping` renames and skips model fields for the outside world.
   You can change the naming convention to ``camelCase`` via the ``name_style`` parameter
   or rename individual fields via ``map``.
#. :func:`.add_property` allows dumping properties of the model like other fields.
#. :func:`.enum_by_exact_value` is the default behavior for all enums.
   It uses enum values without any conversions to represent enum cases.
#. :func:`.enum_by_name` allows representing enums by their names.
#. :func:`.enum_by_value` takes the type of enum values and uses it to load or dump enum cases.


.. _predicate-system:

Predicate system
------------------

So far all examples use classes to apply providers but you can specify other conditions.
There is a single predicate system that is used by most of the builtins providers.

Basic rules:

#. If you pass a class, the provider will be applied to all same types.
#. If you pass an abstract class, the provider will be applied to all subclasses.
#. If you pass a `runtime checkable protocol <https://docs.python.org/3/library/typing.html#typing.runtime_checkable>`_,
   the provider will be applied to all protocol implementations.
#. If you pass a string, it will be interpreted as a regex
   and the provider will be applied to all fields with names matched by the regex.
   Any field name must be a valid python identifier,
   so if you pass the field name directly, it will match an equal string.

Using string directly for predicate often is inconvenient because it matches fields with the same name in all models.
So there special helper for this case.

.. literalinclude:: examples/tutorial/predicate_system_p.py

``P`` represents pattern of path at structure definition.
``P[Book].created_at`` will match field ``created_at`` only if it placed inside model ``Book``

Some facts about ``P``:

#. ``P['name']`` is the same as ``P.name``
#. ``P[Foo]`` is the same as ``Foo`` predicate
#. ``P[Foo] + P.name`` is the same as ``P[Foo].name``
#. ``P[Foo, Bar]`` matches class ``Foo`` or class ``Bar``
#. ``P`` could be combined via ``|``, ``&``, ``^``, also it can be reversed using ``~``
#. ``P`` can be expanded without limit.
   ``P[Foo].name[Bar].age`` is valid and matches field ``age`` located at model ``Bar``,
   situated at field ``name``, placed at model ``Foo``


Retort extension and combination
-------------------------------------

No changes can be done after the retort creation.
You can only make new retort object based on the existing one

:meth:`~.Retort.replace` method using to change scalar options ``debug_path`` and ``strict_coercion``

.. literalinclude:: examples/tutorial/retort_replace.py

:meth:`~.Retort.extend` method adds items to the recipe beginning.
This allows following the DRY principle.

.. literalinclude:: examples/tutorial/retort_extend.py

You can include one retort to another,
it allows to separates creation of loaders and dumpers for specific types into isolated layers.

.. literalinclude:: examples/tutorial/retort_combination.py

In this example, loader and dumper for ``LiteraryWork`` will be created by ``literature_retort``
(note that ``debug_path`` and ``strict_coercion`` options of upper-level retort do not affects inner retorts).

Retort is provider that proxies search into own recipe, so if you pass retort without a :func:`.bound` wrapper,
it will be used for all loaders and dumpers, overriding all subsequent providers.


Provider chaining
=========================

Sometimes you want to add some additional data processing before or after the existing converter
instead of fully replacement of it. This is called `chaining`.

The third parameter of :func:`.loader` and :func:`.dumper` control the chaining process.
:attr:`.Chain.FIRST` means that the result of the given function
will be passed to the next matched loader/dumper at the recipe,
:attr:`.Chain.LAST` marks to apply your function after generated by the next provider.

.. literalinclude:: examples/tutorial/chaining.py


Validators
------------------

:func:`.validator` is a convenient wrapper over :func:`.loader` and chaining to create a verifier of input data.

.. literalinclude:: examples/tutorial/validators.py

If the test function returns ``False``, the exception will be raised.
You can pass an exception factory
that returns the actual exception or pass the string to raise :class:`~.load_error.ValidationError` instance.


Error handling
==================

All loaders have to throw :class:`~.load_error.LoadError` to signal invalid input data.
Other exceptions mean errors at loaders themselves.
All builtin :class:`~.load_error.LoadError` children are listed at :mod:`adaptix.load_error` subpackage
and designed to produce machine-readable structured errors.

.. literalinclude:: examples/tutorial/load_error.py


Struct path
-----------------

Also, builtin loaders and dumpers save path where error was caused.
This path acts like `JSONPath <https://www.ietf.org/archive/id/draft-ietf-jsonpath-base-09.txt>`_
and point to location inside the input data.

.. literalinclude:: examples/tutorial/struct_path_load_error.py

Furthermore, the path is saved for any unexpected errors:

.. literalinclude:: examples/tutorial/struct_path_unexpected_error.py

As you can see, path elements after dumping are wrapped in :class:`~.struct_path.Attr`.
It is necessary because ``str`` or ``int`` instances mean that data can be accessed via ``[]``.

The path is stored at a special private attribute in the exception object,
so it is not shown at ``__str__`` or ``__repr__`` of exception.
There are two helpers to solve this problem.

First is :class:`~.struct_path.ExcPathRenderer` context manager.
It reraises all exceptions as :class:`~.struct_path.PathedException`
that shows path and origin error at ``__str__``.
This tool should be used only for debugging, developing, and prototyping but never in production.

.. literalinclude:: examples/tutorial/struct_path_render_exc_path.py

The second helper is intended to use at production.
:class:`~.struct_path.StructPathRendererFilter` extracts the path from the exception and injects it as ``struct_path``
attribute of `LogRecord <https://docs.python.org/3/library/logging.html#logging.LogRecord>`_.
You only need to attach the Filter to the corresponding logger (or handler).
This allows to integrate adaptix with error monitoring tools like `Sentry <https://sentry.io/for/python/>`_
or `Datadog <https://docs.datadoghq.com/integrations/python/>`_ using one additional line.

.. literalinclude:: examples/tutorial/struct_path_renderer_filter_json.py

.. dropdown:: Struct path rendering with builtin formatter

  No builtin formatter can render all passed extra data.
  You can only specify the concrete field or create a custom formatter.

  This example works only at python 3.10 and more.

  .. literalinclude:: examples/tutorial/struct_path_renderer_filter.py
