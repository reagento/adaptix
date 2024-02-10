Just use pip to install the library

.. code-block:: text

    pip install adaptix==3.0.0b1


Integrations with 3-rd party libraries are turned on automatically,
but you can install adaptix with `extras <https://packaging.python.org/en/latest/tutorials/installing-packages/#installing-extras>`_
to check that versions are compatible.

There are two variants of extras. The first one checks that the version is the same or newer than the last supported,
the second (strict) additionally checks that the version same or older than the last tested version.

.. list-table::
   :header-rows: 1

   * - Extras
     - Versions bound
   * - ``attrs``
     - ``attrs >= 21.3.0``
   * - ``attrs-strict``
     - ``attrs >= 21.3.0, <= 23.1.0``
