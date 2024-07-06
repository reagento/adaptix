========================
Bugs found in Python
========================

Adaptix is a sophisticated project with scrupulous approach to testing.
This leads to the situation where sometimes bugs are found in the Python interpreter itself.

Type alias cannot be created from type alias
=====================================================

The first release of Python 3.11 contains bug preventing parametrizing type aliases with ``TypeVar``
due to support of ``TypeVarTuple``.
Therefore adaptix couldn't even be imported. The next Python patch fixes this.

:octicon:`mark-github` `Issue #98852 <https://github.com/python/cpython/issues/98852>`__


``date.fromtimestamp(None)`` returns current date
======================================================

CPython has two implementations of ``datatime`` module:
the pure python ``_pydatetime`` and optimized ``_datetime`` written in ``C``.

The ``_pydatetime.date.fromtimestamp`` accepts ``None`` instead of ``int`` and returns current date.
This was occurring due to the usage of the ``time.localtime(t)`` function.

By default, the ``C``-version of module is used, but you can disable it via ``Modules/Setup.local`` file.
Also PyPy uses pure-python version of datetime module that reveals this bug.

``date_by_timestamp`` works the same on any python version.

:octicon:`mark-github` `Issue #120268 <https://github.com/python/cpython/issues/120268>`__
