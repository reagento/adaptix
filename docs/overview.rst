==================
Overview
==================

Adaptix is an extremely flexible and configurable data model conversion library.

.. important::

  It is ready for production!

  The beta version only means there may be some backward incompatible changes, so you need to pin a specific version.


Installation
==================

.. code-block:: text

    pip install adaptix==3.0.0a8


Example
==================

.. literalinclude:: examples/tutorial/tldr.py
   :lines: 2-

Requirements
==================

* Python 3.8+


Use cases
==================

* Validation and transformation of received data for your API.
* Config loading/dumping via codec that produces/takes dict.
* Storing JSON in a database and representing it as a model inside the application code.
* Creating API clients that convert a model to JSON sending to the server.
* Persisting entities at cache storage.
* Implementing fast and primitive ORM.


Advantages
==================

.. include:: readme_advantages.md
   :parser: myst_parser.sphinx_


Further reading
==================

See :ref:`Tutorial` for details about library usage.
