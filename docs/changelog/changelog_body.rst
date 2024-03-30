----------------------------------------------------


.. _v3.0.0b4:

`3.0.0b4 <https://github.com/reagento/adaptix/tree/v3.0.0b4>`_ -- 2024-03-30
============================================================================

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

`3.0.0b3 <https://github.com/reagento/adaptix/tree/v3.0.0b3>`_ -- 2024-03-08
============================================================================

.. _v3.0.0b3-Features:

Features
--------

- :func:`.conversion.link` accepts ``coercer`` parameter. `#256 <https://github.com/reagento/adaptix/issues/256>`_
- Add :func:`.conversion.link_constant` to link constant values and constant factories. `#258 <https://github.com/reagento/adaptix/issues/258>`_
- Add coercer for case when source union is subset of destination union (simple ``==`` check is using). `#242 <https://github.com/reagento/adaptix/issues/242>`_
- No coercer error now contains type information. `#252 <https://github.com/reagento/adaptix/issues/252>`_
- Add coercer for ``Optional[S] -> Optional[D]`` if ``S`` is coercible to ``D``. `#254 <https://github.com/reagento/adaptix/issues/254>`_

.. _v3.0.0b3-Bug Fixes:

Bug Fixes
---------

- Fix ``SyntaxError`` with lambda in :func:`.coercer`. `#243 <https://github.com/reagento/adaptix/issues/243>`_
- Model dumping now trying to save the original order of fields inside the dict. `#247 <https://github.com/reagento/adaptix/issues/247>`_
- Fix introspection of sqlalchemy models with ``column_property`` (all ColumnElement is ignored excepting Column itself). `#250 <https://github.com/reagento/adaptix/issues/250>`_

----------------------------------------------------


.. _v3.0.0b2:

`3.0.0b2 <https://github.com/reagento/adaptix/tree/v3.0.0b2>`_ -- 2024-02-16
============================================================================

.. _v3.0.0b2-Features:

Features
--------

- New **major** feature is out!
  Added support for model conversion!
  Now, you can generate boilerplate converter function by adaptix.
  See :ref:`conversion tutorial <conversion-tutorial>` for details.
- Basic support for sqlalchemy models are added!
- Added enum support inside Literal. `#178 <https://github.com/reagento/adaptix/issues/178>`_
- Added flags support.

  Now adaptix has two different ways to process flags: :func:`.flag_by_exact_value` (by default)
  and :func:`.flag_by_member_names`. `#197 <https://github.com/reagento/adaptix/issues/197>`_
- Added defaultdict support. `#216 <https://github.com/reagento/adaptix/issues/216>`_
- Added support of mapping for :func:`.enum_by_name` provider. `#223 <https://github.com/reagento/adaptix/issues/223>`_
- Created the correct path (fixing python bug) for processing ``Required`` and ``NotRequired`` with stringified annotations
  or ``from __future__ import annotations``. `#227 <https://github.com/reagento/adaptix/issues/227>`_

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

- Fixed parameter shuffling on skipping optional field. `#229 <https://github.com/reagento/adaptix/issues/229>`_

----------------------------------------------------


.. _v3.0.0b1:

`3.0.0b1 <https://github.com/reagento/adaptix/tree/v3.0.0b1>`_ -- 2023-12-16
============================================================================

Start of changelog.
