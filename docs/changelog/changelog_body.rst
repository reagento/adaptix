----------------------------------------------------


.. _v3.0.0b11:

`3.0.0b11 <https://github.com/reagento/adaptix/tree/v3.0.0b11>`__ -- 2025-05-09
===============================================================================

.. _v3.0.0b11-Features:

Features
--------


- Completely redesigned error rendering system.
  All errors related to loader, dumper, and converter generation now utilize a new compact and intuitive display format.
  Error messages have also been substantially improved for clarity.

  .. code-block:: text
     :caption: Old error example

        | adaptix.AggregateCannotProvide: Cannot create loader for model. Loaders for some fields cannot be created (1 sub-exception)
        | Location: `Book`
        +-+---------------- 1 ----------------
          | adaptix.AggregateCannotProvide: Cannot create loader for model. Cannot fetch InputNameLayout (1 sub-exception)
          | Location: `Book.author: Person`
          +-+---------------- 1 ----------------
            | adaptix.CannotProvide: Required fields ['last_name'] are skipped
            | Location: `Book.author: Person`
            +------------------------------------

      The above exception was the direct cause of the following exception:

      Traceback (most recent call last):
        ...
      adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.Book'>
      Note: The attached exception above contains verbose description of the problem


  .. code-block:: text
     :caption: New error example

      Traceback (most recent call last):
        ...
      adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.Book'>
        × Cannot create loader for model. Loaders for some fields cannot be created
        │ Location: ‹Book›
        ╰──▷ Cannot create loader for model. Cannot fetch `InputNameLayout`
           │ Location: ‹Book.author: Person›
           ╰──▷ Required fields ['last_name'] are skipped

.. _v3.0.0b11-Breaking Changes:

Breaking Changes
----------------

- Custom iterable subclasses are no longer supported.
  To use them, register via the internal (temporary) API with IterableProvider.
- The ``Retort.replace`` method now requires ``Omitted`` instead of ``None`` to skip parameter values.
- Removed the ``hide_traceback`` parameter from ``Retort`` and ``Retort.replace``.
  Error rendering is now controlled via the ``error_renderer`` parameter.
  Pass ``None`` to display raw Python ``ExceptionGroup`` traces.

.. _v3.0.0b11-Bug Fixes:

Bug Fixes
---------

- Fixed incorrect classification of parametrized generic Pydantic models as iterables
  (due to Pydantic model instances being inherently iterable).
- Corrected hint generation errors during model conversion.
- Fixed handling of parametrized TypeAlias.

----------------------------------------------------


.. _v3.0.0b10:

`3.0.0b10 <https://github.com/reagento/adaptix/tree/v3.0.0b10>`__ -- 2025-04-13
===============================================================================

.. _v3.0.0b10-Features:

Features
--------

- Add support for msgspec models!

  Now you can work with msgspec models like any other:
  construct from a dict, serialize to a dict, and convert it into any other model.

  Also, you can use ``integrations.msgspec.native_msgspec`` to delegate loading and dumping to msgspec itself.

  This allows you to combine the flexibility of adaptix with the incredible speed of msgspec

- A completely new algorithm for model dumper code generation has been implemented.

  Dumping models with default values is now faster. For GitHub Issues models, which include only a few default fields, dump time has been reduced by 22%.
- Now you can easily distinguish between a missing field and a None value.
  The new :func:`.as_sentinel` function allows you to mark types as sentinels,
  ensuring they remain hidden from the outside world.
  See :ref:`detecting-absense-of-a-field` for detail. `#214 <https://github.com/reagento/adaptix/issues/214>`__
- Add support for ``ZoneInfo``. `#375 <https://github.com/reagento/adaptix/issues/375>`__


.. _v3.0.0b10-Breaking Changes:

Breaking Changes
----------------

- Changed the signature of the :func:`.integrations.pydantic.native_pydantic` function.
  Now, parameters for validator and serializer are grouped into dictionaries.

.. _v3.0.0b10-Bug Fixes:

Bug Fixes
---------

- Fix default values loading for types inherited from builtin types. `#363 <https://github.com/reagento/adaptix/issues/363>`__
- Fix the error caused by using with_property when the function was used only once for a type.

.. _v3.0.0b10-Other:

Other
-----

- Internal benchmarking framework now can use SQLite to store result data `#370 <https://github.com/reagento/adaptix/issues/370>`__
- Add Gurubase AI to documentation

----------------------------------------------------


.. _v3.0.0b9:

`3.0.0b9 <https://github.com/reagento/adaptix/tree/v3.0.0b9>`__ -- 2024-12-15
=============================================================================

.. _v3.0.0b9-Features:

Features
--------

- Add support for all Python 3.13 new features.

.. _v3.0.0b9-Breaking Changes:

Breaking Changes
----------------

- All iterables now are dumped to tuple (or list for list children). `#348 <https://github.com/reagento/adaptix/issues/348>`__

.. _v3.0.0b9-Bug Fixes:

Bug Fixes
---------

- Fix ``NoRequiredFieldsLoadError`` raising for fields generated by name flattening.
- ``hide_traceback=False`` shows traceback now.

.. _v3.0.0b9-Other:

Other
-----

- Add "Why not Pydantic?" article.

----------------------------------------------------


.. _v3.0.0b8:

`3.0.0b8 <https://github.com/reagento/adaptix/tree/v3.0.0b8>`__ -- 2024-09-02
=============================================================================

.. _v3.0.0b8-Features:

Features
--------

- Add new :func:`.datetime_by_timestamp` and :func:`.date_by_timestamp` provider factories. `#281 <https://github.com/reagento/adaptix/issues/281>`__
- Add :func:`.datetime_by_format` to public API. `#286 <https://github.com/reagento/adaptix/issues/286>`__
- Add :func:`.type_tools.exec_type_checking` function
  to deal with cyclic references by executing ``if TYPE_CHECKING:`` constructs. `#288 <https://github.com/reagento/adaptix/issues/288>`__
- Add support for bytes inside literal, for example ``Literal[b"abc"]``. `#318 <https://github.com/reagento/adaptix/issues/318>`__
- The library shows a hint if one class is a model and the other is not.
- Traceback of ``CannotProvide`` is hidden (it is raised when loader, dumper, or converter can not be created).
  It simplifies error messages to users.
  You can show traceback by disabling ``hide_traceback`` parameter of ``Retort``.

.. _v3.0.0b8-Breaking Changes:

Breaking Changes
----------------

- Drop support of Python 3.8.
- ``TypedDictAt38Warning`` is removed.

.. _v3.0.0b8-Other:

Other
-----

- Refactor internal provider routing system. It becomes more simple and readable.
  Also, internal caching is added.
  This led to a 40% speedup in loader generation for medium models
  and up to 4x speedup for large models with many recursive types.

----------------------------------------------------


.. _v3.0.0b7:

`3.0.0b7 <https://github.com/reagento/adaptix/tree/v3.0.0b7>`__ -- 2024-06-10
=============================================================================

.. _v3.0.0b7-Deprecations:

Deprecations
------------

- ``NoSuitableProvider`` exception was renamed to ``ProviderNotFoundError``. `#245 <https://github.com/reagento/adaptix/issues/245>`__

.. _v3.0.0b7-Bug Fixes:

Bug Fixes
---------

- Allow redefining coercer inside ``Optional`` using an inner type if source and destination types are same. `#279 <https://github.com/reagento/adaptix/issues/279>`__
- Fix ``ForwardRef`` evaluation inside bound of ``TypeVar`` for ``Python 3.12.4``. `#312 <https://github.com/reagento/adaptix/issues/312>`__

----------------------------------------------------


.. _v3.0.0b6:

`3.0.0b6 <https://github.com/reagento/adaptix/tree/v3.0.0b6>`__ -- 2024-05-23
=============================================================================

.. _v3.0.0b6-Features:

Features
--------

- Now, you can merge several fields or access the model directly via :func:`.conversion.link_function`.

  See :ref:`link_function` for details.

- Add a special column type for serializing and deserializing JSON inside SQLAlchemy.

  See :ref:`sqlalchemy_json` for details.

- Add ``Extended Usage`` article for model conversion and other documentation updates.

.. _v3.0.0b6-Bug Fixes:

Bug Fixes
---------

- Fix processing of list relationships in SQLAlchemy.

- Fix model loader generation with non-required field and ``DebugTrail.DISABLE``.

----------------------------------------------------


.. _v3.0.0b5:

`3.0.0b5 <https://github.com/reagento/adaptix/tree/v3.0.0b5>`__ -- 2024-04-20
=============================================================================

.. _v3.0.0b5-Features:

Features
--------

- Add support for Pydantic models!

  Now you can work with pydantic models like any other:
  construct from dict, serialize to dict, and convert it to any other model.

  Also, you can use :func:`.integrations.pydantic.native_pydantic` to delegate loading and dumping to pydantic itself.

- Add support for dumping ``Literal`` inside ``Union``. `#237 <https://github.com/reagento/adaptix/issues/237>`__
- Add support for ``BytesIO`` and ``IO[bytes]``. `#270 <https://github.com/reagento/adaptix/issues/270>`__
- Error messages are more obvious.

.. _v3.0.0b5-Breaking Changes:

Breaking Changes
----------------

- Forbid use of constructs like ``P[SomeClass].ANY`` because it is misleading (you have to use ``P.ANY`` directly).
- Private fields (any field starting with underscore) are skipped at dumping.
  See :ref:`private_fields_dumping` for details.

----------------------------------------------------


.. _v3.0.0b4:

`3.0.0b4 <https://github.com/reagento/adaptix/tree/v3.0.0b4>`__ -- 2024-03-30
=============================================================================

.. _v3.0.0b4-Features:

Features
--------

- Add coercer for builtin iterables and dict.
- Models can be automatically converted inside compound types like ``Optional``, ``list``, ``dict`` etc.
- Add :func:`.conversion.from_param` predicate factory to match only parameters
- An error of loader, dumper, and converter generation contains a much more readable location.

  For example:

  - ``Linking: `Book.author_ids: list[int] -> BookDTO.author_ids: list[str]```
  - ``Location: `Stub.f3: memoryview```

.. _v3.0.0b4-Breaking Changes:

Breaking Changes
----------------

- Now, parameters are automatically linked only to top-level model fields.
  For manual linking, you can use the new :func:`adaptix.conversion.from_param` predicate factory.

.. _v3.0.0b4-Bug Fixes:

Bug Fixes
---------

- Fix fail to import adaptix package on python 3.8-3.10 when ``-OO`` is used.
- Fix unexpected error on creating coercer between fields with ``Optional`` type.
- Fix unexpected error with type vars getting from ``UnionType``.

----------------------------------------------------


.. _v3.0.0b3:

`3.0.0b3 <https://github.com/reagento/adaptix/tree/v3.0.0b3>`__ -- 2024-03-08
=============================================================================

.. _v3.0.0b3-Features:

Features
--------

- :func:`.conversion.link` accepts ``coercer`` parameter. `#256 <https://github.com/reagento/adaptix/issues/256>`__
- Add :func:`.conversion.link_constant` to link constant values and constant factories. `#258 <https://github.com/reagento/adaptix/issues/258>`__
- Add coercer for case when source union is subset of destination union (simple ``==`` check is using). `#242 <https://github.com/reagento/adaptix/issues/242>`__
- No coercer error now contains type information. `#252 <https://github.com/reagento/adaptix/issues/252>`__
- Add coercer for ``Optional[S] -> Optional[D]`` if ``S`` is coercible to ``D``. `#254 <https://github.com/reagento/adaptix/issues/254>`_

.. _v3.0.0b3-Bug Fixes:

Bug Fixes
---------

- Fix ``SyntaxError`` with lambda in :func:`.coercer`. `#243 <https://github.com/reagento/adaptix/issues/243>`__
- Model dumping now trying to save the original order of fields inside the dict. `#247 <https://github.com/reagento/adaptix/issues/247>`__
- Fix introspection of sqlalchemy models with ``column_property`` (all ColumnElement is ignored excepting Column itself). `#250 <https://github.com/reagento/adaptix/issues/250>`__

----------------------------------------------------


.. _v3.0.0b2:

`3.0.0b2 <https://github.com/reagento/adaptix/tree/v3.0.0b2>`__ -- 2024-02-16
=============================================================================

.. _v3.0.0b2-Features:

Features
--------

- New **major** feature is out!
  Added support for model conversion!
  Now, you can generate boilerplate converter function by adaptix.
  See :ref:`conversion tutorial <conversion-tutorial>` for details.
- Basic support for sqlalchemy models are added!
- Added enum support inside Literal. `#178 <https://github.com/reagento/adaptix/issues/178>`__
- Added flags support.

  Now adaptix has two different ways to process flags: :func:`.flag_by_exact_value` (by default)
  and :func:`.flag_by_member_names`. `#197 <https://github.com/reagento/adaptix/issues/197>`__
- Added defaultdict support. `#216 <https://github.com/reagento/adaptix/issues/216>`__
- Added support of mapping for :func:`.enum_by_name` provider. `#223 <https://github.com/reagento/adaptix/issues/223>`__
- Created the correct path (fixing python bug) for processing ``Required`` and ``NotRequired`` with stringified annotations
  or ``from __future__ import annotations``. `#227 <https://github.com/reagento/adaptix/issues/227>`__

.. _v3.0.0b2-Breaking Changes:

Breaking Changes
----------------

- Due to refactoring of predicate system required for new features:

  1. ``create_request_checker`` was renamed to ``create_loc_stack_checker``
  2. ``RequestPattern`` (class of ``P``) was renamed to ``LocStackPattern``
  3. method ``RequestPattern.build_request_checker()`` was renamed to ``LocStackPattern.build_loc_stack_checker()``

.. _v3.0.0b2-Deprecations:

Deprecations
------------

- Standardize names inside :mod:`adaptix.load_error`. Import of old names will emit ``DeprecationWarning``.

  .. list-table::
     :header-rows: 1

     * - Old name
       - New name
     * - ``MsgError``
       - ``MsgLoadError``
     * - ``ExtraFieldsError``
       - ``ExtraFieldsLoadError``
     * - ``ExtraItemsError``
       - ``ExtraItemsLoadError``
     * - ``NoRequiredFieldsError``
       - ``NoRequiredFieldsLoadError``
     * - ``NoRequiredItemsError``
       - ``NoRequiredItemsLoadError``
     * - ``ValidationError``
       - ``ValidationLoadError``
     * - ``BadVariantError``
       - ``BadVariantLoadError``
     * - ``DatetimeFormatMismatch``
       - ``FormatMismatchLoadError``

.. _v3.0.0b2-Bug Fixes:

Bug Fixes
---------

- Fixed parameter shuffling on skipping optional field. `#229 <https://github.com/reagento/adaptix/issues/229>`__

----------------------------------------------------


.. _v3.0.0b1:

`3.0.0b1 <https://github.com/reagento/adaptix/tree/v3.0.0b1>`__ -- 2023-12-16
=============================================================================

Start of changelog.
