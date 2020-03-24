***********
Quickstart
***********

Installation
=============

Just use pip to install the library::

    pip install dataclass_factory



Simple case
==============

All you have to do to start pasring you dataclasses is create a Factory instance.
Then call ``load`` or ``dump`` methods with corresponding type and everything is done automatically.

.. literalinclude:: examples/tldr.py

All typing information is retrieved from you annotations, so it is not required from you to provide any schema or even change your dataclass decorators or class bases

It is better to create factory only once, because all parsers are cached inside it after first usage.
Otherwise, the structure of your classes will be analysed again and again for every new instance of Factory.

Nested objects
====================

Nested objects are supported out of the box. It is surprising, but you do not have to do anything except defining your dataclasses.

.. literalinclude:: examples/nested.py


Lists and other collections
============================



.. literalinclude:: examples/collection.py


Validation
===================

.. literalinclude:: examples/validation.py