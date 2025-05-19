=====================
Why not Pydantic?
=====================


Introduction
====================

Pydantic is one of the most popular libraries for data serialization and deserialization.
However, the principles it’s built on often prevent ease of use.

In this article, we’ll explore how using Adaptix instead of Pydantic can help manage common tasks more efficiently.

.. note::

  This article is updated for ``pydantic==2.9.2``, with code snippets run on ``CPython`` version ``3.12``.
  Some things may have changed since then, but probably not much.


The Main Thesis
=====================

Pydantic works smoothly only when you violate the Single Responsibility Principle (SRP).
It wants to know about your domain layer, it wants to penetrate it.
Pydantic performs best when it's simultaneously a (de)serializer for incoming requests and a domain model.
However, separating your code into layers can lead to challenges when transferring data between them.

Let's imagine that you have three nested domain dataclasses.
It works fine for a while, and then you add a new field to the deepest model and
discover that Pydantic doesn't include the UTC offset in the datetime string
(or it has any other unwanted behavior).

Your possible options:

* Completely duplicate the dataclass structure, including all nested models,
  into an equivalent Pydantic model with the necessary config.
* Perform manual serialization.
* Start using Adaptix.

And what you get after switching:

* Nothing invades your domain layer, the serialization logic lives entirely in the presentation layer.
* Decreased code coupling.
* You can use adaptix to convert models passing between layers.

Why can't I just use Pydantic as the domain model? Well, let’s talk about that.


Pydantic's pitfalls
==========================


Coupling instance creation and data parsing
-------------------------------------------------

Creating any model instance in Pydantic triggers data parsing.
On one hand, this makes instance creation within a program significantly more resource-intensive,
while on the other, it can lead to unexpected and undesirable behavior during instance creation.
Let’s examine this in detail.


Instantiation penalty
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let’s take a model from the Pydantic tutorial:

.. literalinclude:: /examples/why_not_pydantic/instantiating_penalty_models.py


And run a simple benchmark for creating instances:

.. literalinclude:: /examples/why_not_pydantic/instantiating_penalty_benchmark.py
   :lines: 2-

Here are the results:

.. code-block::

   pydantic  2.3817247649421915
   dataclass 0.9756000880151987

Creating a Pydantic model instance is nearly 2.4 times slower than creating a similar dataclass instance.
This performance overhead is the cost you’ll pay each time you create an object in your business logic.

But Pydantic has a method, ``.model_construct()``, for creating instances without validation!
And yet, it’s even slower:

.. literalinclude:: /examples/why_not_pydantic/instantiating_penalty_benchmark_model_construct.py
   :lines: 2-

.. code-block::

   pydantic (model_construct) 2.8749908979516476


.. dropdown:: Some notes on the benchmarks

   In fact, a significant portion of the time in the benchmark above is spent creating a ``datetime`` object.
   If we remove this object creation, the situation becomes even more dramatic:

   .. literalinclude:: /examples/why_not_pydantic/instantiating_penalty_benchmark_datetime.py
      :lines: 2-

   .. code-block::

       pydantic                   1.8139039139496163
       pydantic (model_construct) 2.155639562988654
       dataclass                  0.4947519419947639

   Now Pydantic is 3.7 times slower than a standard dataclass,
   and 4.3 times slower if you attempt to disable validation.

   Pydantic's slowdown factor will vary depending on the complexity of the validation and
   the time required to create other classes.


Fused validation
^^^^^^^^^^^^^^^^^^^^^^^

Validating invariants within the model is reasonable,
but validation should be separated into business logic and representation layers.

For example, type checking prevents most type-related errors,
and having basic tests eliminates them altogether.
Do you really need type checks each time you create a model instance?
What if the model includes large lists?

Let’s look at how ``attrs`` approaches this issue.
Models of ``attrs`` can’t transform themselves into JSON or load themselves from JSON.
External tools (such as ``adaptix`` or ``cattrs``) handle this functionality.

Within the model, you can declare validators to enforce business invariants,
while Adaptix can perform additional checks when loading data from an untrusted source.

You can also use the ``__post_init__`` method in dataclasses for necessary validation.

As a result, with Pydantic you can either constantly run checks that you don't need at all,
or skip any validation at all using ``.model_construct()``
(which will most likely be even slower, as shown above).


Implicit conversions
^^^^^^^^^^^^^^^^^^^^^^^

The next issue lies in the fact that implicit type conversion logic, suitable for parsing,
is often inappropriate for creating an object via a constructor.

For a parser, it’s entirely reasonable to perform implicit conversions
(such as `TolerantReader <https://martinfowler.com/bliki/TolerantReader.html>`__).
However, this behavior can lead to errors when applied within a program.

For example, if you pass a ``float`` value to a field with the ``Decimal`` type,
Pydantic will implicitly convert it instead of raising an error.
This leads to the possibility
that the error of using floats for monetary calculations can be hidden,
potentially causing inaccuracies.

.. literalinclude:: /examples/why_not_pydantic/implicit_conversions.py
   :caption: Possible loss of accuracy
   :lines: 2-

There is a way to work around this issue.
To do so, you must enable strict mode and disable it each time model parsing occurs.

.. literalinclude:: /examples/why_not_pydantic/implicit_conversions_workaround.py
   :caption: Necessary workaround to avoid loss of accuracy
   :lines: 2-


Aliasing mess
^^^^^^^^^^^^^^^^^^^^^^^

The essence of aliases is that you have an external and an internal field name,
where the external name is unsuitable for use within the program.
However, the Pydantic combines different representations into a ball of mud.

By default, the constructor only accepts fields by their aliases (i.e., using the external names).
You can change this with the ``populate_by_name`` configuration option.
This option allows you to use the internal field names in the constructor
while still accepting the external representation.
Additionally, this option affects JSON parsing, enabling it to use field names alongside aliases.

.. literalinclude:: /examples/why_not_pydantic/aliasing_mess_extra.py
   :caption: Extra field is parsed as usual field


Mistakes silencing
^^^^^^^^^^^^^^^^^^^^^^^

One of the biggest issues with Pydantic’s approach is that extra fields passed into the constructor are ignored.
As a result, such typos do not show up immediately,
but remain in the program until discovered by tests or users.

Static analyzers can reduce the number of such errors,
but this does not always work due to the dynamic nature of Python.

You can forbid additional fields by setting ``extra='forbid'``,
though this will also affect the parser.

.. literalinclude:: /examples/why_not_pydantic/mistakes_silencing.py
   :caption: Extra field is ignored
   :lines: 2-


Locking ecosystem
------------------------------

Pydantic’s primary purpose is data serialization and deserialization.
Instead of using standard library models (``@dataclass``, ``NamedTuple``, ``TypedDict``),
Pydantic introduces a new model type, even though these tasks don’t necessitate a new model type.

Pydantic models come with unique semantics,
requiring special support from development tools like type checkers and IDEs.
Most importantly, external libraries that don’t care about the serialization method still must add
support for Pydantic models, creating dependencies on these integrations.

Pydantic does support standard library models, but this support is very limited.
For example, you can’t alter parsing or serialization logic in an existing class.

You can avoid these issues by restricting Pydantic to the layer responsible for communication with the outer world.
However, this requires duplicating classes and manually writing converters.
Pydantic offers a ``from_attributes=True`` mode,
which allows you to create model instances from other objects,
though it has significant limitations.


Underdone class mapping
------------------------------

Pydantic offers limited support for transforming one model into another.
It behaves like a regular validation mode for an unknown source,
except instead of referencing dictionary keys, it accesses object attributes.

.. literalinclude:: /examples/why_not_pydantic/underdone_class_mapping_intro.py
   :caption: Model mapping in Pydantic

This results in several issues:

First, the ``from_attributes=True`` mode uses the same aliases as parsing.
You cannot configure transformations without affecting the logic for external interactions (like JSON parsing).

Second, mapping does not account for type hints from the source class, leading to unnecessary type checks.
For example, if both classes contain fields with values of type ``list[str]`` with hundreds of elements,
Pydantic will check the type of each value.

Third, you can't customize class mapping so that the conversion logic differs from parsing from an unknown source.
You are forced to either find workarounds or change interactions with the outside world.

Fourth, there are no checks to ensure the mapping between the target class and the source is correctly defined.
Many such errors are caught in tests when the code fails with an error,
but some are only noticeable upon careful result comparison,
such as if a field in the target model has a default value.

.. literalinclude:: /examples/why_not_pydantic/underdone_class_mapping_default.py
   :caption: Skipped error
   :lines: 2-


.. hint::

  You can use Adaptix’s class conversion with Pydantic models,
  eliminating all the problems listed above (except for the second point).
  See :ref:`conversion tutorial <Conversion-tutorial>` and :ref:`supported-model-kinds` for details.


One presentation ought to be enough for anybody
----------------------------------------------------

Pydantic tightly binds parsing rules to the model itself.
This creates major issues when loading or exporting the model differently based on use cases.

For example, you might load a config from various formats.
While the structure of the config is generally similar,
it may differ in how certain types are loaded and in field naming conventions.

Or consider having a common user model,
but needing to return a different field set for different clients.

The only way to get around this problem is to try to use the ``context`` parameter
and write dispatch logic inside the validators.


Pydantic is written in Rust, so Pydantic is fast?
------------------------------------------------------

As benchmarks show, this is far from true.

To be cautious, Pydantic’s speed is approximately equal to libraries written in Python and using code generation.

Speaking more boldly, in some cases, Adaptix outperforms Pydantic by a factor of two
without losing in any benchmark, and PyPy usage can significantly speed up Adaptix.

For more detail, see :ref:`benchmarks`.



About Adaptix
==========================


The Philosophy
---------------------------------


Adaptix does not offer a new special model that requires IDE and type checker support.
It works with any model you like
(``@dataclass``, ``attrs``, and even Pydantic, see full list at :ref:`supported-model-kinds`).

Adaptix does not affect the model definition.
You create a special object that implements the loading and dumping of models.
This object is called a `Retort` (the name of a chemical device used to distill substances).

For each presentation format, you create a new retort instance.
You can extend and combine instances to eliminate code duplication.

So, you have:
  * Models defined inside your business logic layer (these classes know nothing about serialization mechanism),
  * Retorts know how to transform these classes into outer formats.

Such separation allows you to keep your code clean and simple.
Also, you can create one retort instance to handle dozens of classes
following similar principles of outer representation.

See :ref:`loading and dumping tutorial <loading-and-dumping-tutorial>` for details.

But that's not all. Adaptix can generate object mappers.
Such converters are vital for layered applications
but they are very boring to write and error-prone to maintain.
For the same or similar models, you can produce a converter using one line of code.
This converter knows about two models but does not affect them.

See :ref:`conversion tutorial <conversion-tutorial>` for details.


Unmentioned advantages
---------------------------------

All the issues mentioned above highlight problems that don’t arise when using Adaptix.
However, there are aspects that cannot be counted as issues with Pydantic,
but they could highlight Adaptix in comparison.

Firstly, Adaptix has a predicate system that allows granular customization of behavior.
You can adjust behavior for groups of classes or for a type only if it is within a specific class.
You can also configure logic separately for dictionary keys and values, even if they share the same type.
See :ref:`predicate-system` for details.

Secondly, Adaptix is designed to provide the maximum number of opportunities to follow the DRY (Don't Repeat Yourself) principle.

* You can override behavior for entire groups of fields and types using the predicate system mentioned earlier.
* You can inherit rule groups, reducing code duplication.
* You can separate rules into several isolated layers, simplifying complex transformation cascades.

For more information on these capabilities, see :ref:`retort_extension_and_combination`.


Migrating from Pydantic
---------------------------------

Adaptix provides several tools for a gradual migration from Pydantic.

First, Adaptix supports Pydantic models.
You can load and dump Pydantic models just as you would with ``@dataclass``, ``NamedTuple``, ``TypedDict``, and others.
This method ignores alias settings within the model itself, with all transformation logic defined in the retort.
Adaptix parses the input data and passes it to the model’s constructor.
See :ref:`supported-model-kinds` for details.

.. literalinclude:: /examples/why_not_pydantic/migration_pydantic_model.py
   :caption: Loading and dumping Pydantic model


Second, you can delegate handling of specific types directly to Pydantic with
:func:`.integrations.pydantic.native_pydantic`.
Using the built-in predicate system,
you can control behavior more granularly than Pydantic itself allows
(see :ref:`predicate-system` for details).

.. literalinclude:: /examples/reference/integrations/native_pydantic.py
   :caption: Delegating to Pydantic


Conclusion
=====================

While Pydantic has been a popular choice for data serialization and validation in Python,
it comes with notable drawbacks that can complicate software development, particularly in layered architectures.
Its tight coupling of validation, serialization, and domain modeling often violates the Single Responsibility Principle,
leading to issues such as unnecessary complexity, inefficiency, and loss of flexibility.

Adaptix, by contrast, offers a more modular and developer-friendly approach.
By decoupling serialization logic from domain models, it allows for cleaner code, easier maintenance,
and more efficient operations. Whether it’s class mapping, custom validation, or handling diverse data formats,
Adaptix delivers robust solutions that avoid the pitfalls commonly encountered with Pydantic.
