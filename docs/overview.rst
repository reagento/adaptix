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

    pip install adaptix==3.0.0b10


Example
==================

.. literalinclude:: /examples/loading-and-dumping/tutorial/tldr.py
   :caption: Model loading and dumping
   :name: loading-and-dumping-example

.. literalinclude:: /examples/conversion/tutorial/tldr.py
   :caption: Conversion one model to another
   :name: conversion-example

Requirements
==================

* Python 3.9+


Use cases
==================

* Validation and transformation of received data for your API.
* Conversion between data models and DTOs.
* Config loading/dumping via codec that produces/takes dict.
* Storing JSON in a database and representing it as a model inside the application code.
* Creating API clients that convert a model to JSON sending to the server.
* Persisting entities at cache storage.
* Implementing fast and primitive ORM.


Advantages
==================

.. include:: /readme_advantages.md
   :parser: myst_parser.sphinx_


Further reading
==================

See :ref:`loading and dumping tutorial <loading-and-dumping-tutorial>`
and :ref:`conversion tutorial <conversion-tutorial>` for details about library usage.
