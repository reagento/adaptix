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
  2. ``LocStackPattern`` (class of ``P``) was renamed ``RequestPattern``
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
