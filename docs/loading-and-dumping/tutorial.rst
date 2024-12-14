.. _loading-and-dumping-tutorial:

***********
Tutorial
***********

Adaptix analyzes your type hints and generates corresponding transformers based on the retrieved information.
You can flexibly tune the conversion process following DRY principle.

Installation
=============

.. include:: /common/installation.rst

Introduction
====================

The central object of the library is `Retort`.
It can create models from mapping (loading) and create mappings from the model (dumping).


.. literalinclude:: /examples/loading-and-dumping/tutorial/tldr.py

All typing information is retrieved from your annotations, so is not required from you to provide any additional schema
or even change your dataclass decorators or class bases.

In the provided example ``book.author == "Unknown author"`` because normal dataclass constructor is called.

It is better to create a retort only once because all loaders are cached inside it after the first usage.
Otherwise, the structure of your classes will be analyzed again and again for every new instance of Retort.

If you don't need any customization, you can use the predefined :func:`.load` and :func:`.dump` functions.

Nested objects
--------------------

Nested objects are supported out of the box. It is surprising,
but you do not have to do anything except define your dataclasses.
For example, you expect that the author of the Book is an instance of a Person, but in the dumped form it is a dictionary.

Declare your dataclasses as usual and then just load your data.

.. literalinclude:: /examples/loading-and-dumping/tutorial/nested.py


Lists and other collections
--------------------------------

Want to load a collection of dataclasses?
No changes are required, just specify the correct target type (e.g ``List[SomeClass]`` or ``Dict[str, SomeClass]``).

.. literalinclude:: /examples/loading-and-dumping/tutorial/collection.py

Fields also can contain any supported collections.

.. _retort-configuration:

Retort configuration
======================

There are two parameters that :class:`.Retort` constructor takes.

:paramref:`debug_trail` is responsible for saving the place where the exception was caused.
By default, retort saves all raised errors (including unexpected ones) and the path to them.
If data is loading or dumping from a trusted source where an error is unlikely,
you can change this behavior to saving only the first error with trail or without trail.
It will slightly improve performance if no error is caused and will have more impact if an exception is raised.
More details about working with the saved trail in :ref:`Error handling`

:paramref:`strict_coercion` affects only the loading process.
If it is enabled (this is the default state) type will be converted only two conditions passed:

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
It implements `chain-of-responsibility <https://en.wikipedia.org/wiki/Chain-of-responsibility_pattern>`__
design pattern.
The recipe consists of `providers`, each of which can precisely override one of the retort's behavior aspects.

.. literalinclude:: /examples/loading-and-dumping/tutorial/retort_recipe_intro.py

Default ``datetime`` loader accepts only ``str`` in ``ISO 8601`` format,
``loader(datetime, lambda x: datetime.fromtimestamp(x, tz=timezone.utc))``
replaces it with a specified lambda function that takes ``int`` representing ``Unix time``.

.. dropdown:: Same example but with a dumper

  .. literalinclude:: /examples/loading-and-dumping/tutorial/retort_recipe_intro_dumper.py

Providers at the start of the recipe have higher priority because they overlap subsequent ones.

.. literalinclude:: /examples/loading-and-dumping/tutorial/recipe_providers_priority.py

Basic providers overview
---------------------------

The list of providers is not limited to :func:`.loader` and :func:`.dumper`,
there are a lot of other high-level helpers. Here are some of them.

#. :func:`.constructor` creates a loader that extracts data from dict and passes it to the given function.
#. :func:`.name_mapping` renames and skips model fields for the outside world.
   You can change the naming convention to ``camelCase`` via the ``name_style`` parameter
   or rename individual fields via ``map``.
#. :func:`.with_property` allows dumping properties of the model like other fields.
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
#. If you pass a `runtime checkable protocol <https://docs.python.org/3/library/typing.html#typing.runtime_checkable>`__,
   the provider will be applied to all protocol implementations.
#. If you pass a string, it will be interpreted as a regex
   and the provider will be applied to all fields with id matched by the regex.
   In most cases, ``field_id`` is the name of the field at class definition.
   Any field_id must be a valid python identifier,
   so if you pass the ``field_id`` directly, it will match an equal string.

Using string directly for predicate often is inconvenient because it matches fields with the same name in all models.
So there special helper for this case.

.. literalinclude:: /examples/loading-and-dumping/tutorial/predicate_system_p.py

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


.. _retort_extension_and_combination:

Retort extension and combination
-------------------------------------

No changes can be made after the retort creation.
You can only make new retort object based on the existing one

:meth:`~.Retort.replace` method using to change scalar options ``debug_trail`` and ``strict_coercion``

.. literalinclude:: /examples/loading-and-dumping/tutorial/retort_replace.py

:meth:`~.Retort.extend` method adds items to the recipe beginning.
This allows following the DRY principle.

.. literalinclude:: /examples/loading-and-dumping/tutorial/retort_extend.py

You can include one retort to another,
it allows to separate creation of loaders and dumpers for specific types into isolated layers.

.. literalinclude:: /examples/loading-and-dumping/tutorial/retort_combination.py

In this example, loader and dumper for ``LiteraryWork`` will be created by ``literature_retort``
(note that ``debug_trail`` and ``strict_coercion`` options of upper-level retort do not affects inner retorts).

Retort is provider that proxies search into their own recipe, so if you pass retort without a :func:`.bound` wrapper,
it will be used for all loaders and dumpers, overriding all subsequent providers.


Provider chaining
=========================

Sometimes you want to add some additional data processing before or after the existing converter
instead of fully replacing it. This is called `chaining`.

The third parameter of :func:`.loader` and :func:`.dumper` control the chaining process.
:attr:`.Chain.FIRST` means that the result of the given function
will be passed to the next matched loader/dumper at the recipe,
:attr:`.Chain.LAST` marks to apply your function after the one generated by the next provider.

.. literalinclude:: /examples/loading-and-dumping/tutorial/chaining.py


Validators
------------------

:func:`.validator` is a convenient wrapper over :func:`.loader` and chaining to create a verifier of input data.

.. literalinclude:: /examples/loading-and-dumping/tutorial/validators.py

If the test function returns ``False``, the exception will be raised.
You can pass an exception factory
that returns the actual exception or pass the string to raise :class:`~.load_error.ValidationError` instance.

.. dropdown:: Traceback of raised errors

  .. literalinclude:: /examples/loading-and-dumping/tutorial/validators_1.pytb

  .. literalinclude:: /examples/loading-and-dumping/tutorial/validators_2.pytb

.. _Error handling:

Error handling
==================

All loaders have to throw :class:`~.load_error.LoadError` to signal invalid input data.
Other exceptions mean errors at loaders themselves.
All builtin :class:`~.load_error.LoadError` children have listed at :mod:`adaptix.load_error` subpackage
and designed to produce machine-readable structured errors.

.. literalinclude:: /examples/loading-and-dumping/tutorial/load_error_dt_all.py

.. dropdown:: Traceback of raised error (``DebugTrail.ALL``)

  .. literalinclude:: /examples/loading-and-dumping/tutorial/load_error_dt_all.pytb

By default, all thrown errors are collected into :class:`~.load_error.AggregateLoadError`,
each exception has an additional note describing path of place where the error is caused.
This path is called a ``Struct trail`` and acts like
`JSONPath <https://www.ietf.org/archive/id/draft-ietf-jsonpath-base-09.txt>`__
pointing to location inside the input data.

For Python versions less than 3.11, an extra package ``exceptiongroup`` is used.
This package patch some functions from ``traceback``
during import to backport ``ExceptionGroup`` rendering to early versions.
More details at `documentation <https://pypi.org/project/exceptiongroup/>`__.

By default, all collection-like and model-like loaders wrap all errors into :class:`~.load_error.AggregateLoadError`.
Each sub-exception contains a trail relative to the parent exception.

.. custom-non-guaranteed-behavior::

  Order of errors inside :class:`~.load_error.AggregateLoadError` is not guaranteed.


You can set ``debug_trail=DebugTrail.FIRST`` at Retort to raise only the first met error.

.. dropdown:: Traceback of raised error (``DebugTrail.FIRST``)

  .. literalinclude:: /examples/loading-and-dumping/tutorial/load_error_dt_first.pytb

Changing ``debug_trail`` to ``DebugTrail.DISABLE`` make the raised exception act like any normal exception.

.. dropdown:: Traceback of raised error (``DebugTrail.DISABLE``)

  .. literalinclude:: /examples/loading-and-dumping/tutorial/load_error_dt_disable.pytb

If there is at least one unexpected error :class:`~.load_error.AggregateLoadError`
is replaced by standard `ExceptionGroup <https://docs.python.org/3/library/exceptions.html#ExceptionGroup>`__.
For the dumping process any exception is unexpected, so it always will be wrapped with ``ExceptionGroup``

.. literalinclude:: /examples/loading-and-dumping/tutorial/unexpected_error.py
   :lines: 2-

Trail of exception is stored at a special private attribute and could be accessed via :class:`~.struct_trail.get_trail`.

As you can see, trail elements after dumping are wrapped in :class:`~.struct_trail.Attr`.
It is necessary because ``str`` or ``int`` instances mean that data can be accessed via ``[]``.
