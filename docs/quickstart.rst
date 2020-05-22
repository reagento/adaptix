***********
Quickstart
***********

Dataclass factory analyzes your type hints and generates corresponding parsers based on retrieved information.
For dataclasses it checks what fields are declared and then calls normal constructor. For others types behavior can differ.

Also you can configure it using miscellaneous schemas (see :ref:`extended_usage`).

Installation
=============

Just use pip to install the library::

    pip install dataclass_factory



Simple case
==============

All you have to do to start pasring you dataclasses is create a Factory instance.
Then call ``load`` or ``dump`` methods with corresponding type and everything is done automatically.

.. literalinclude:: examples/tldr.py

All typing information is retrieved from you annotations, so it is not required from you to provide any schema or even change your dataclass decorators or class bases.

In provided example ``book.author == "Unknown author"`` because normal dataclass constructor is called.

It is better to create factory only once, because all parsers are cached inside it after first usage.
Otherwise, the structure of your classes will be analysed again and again for every new instance of Factory.


.. _nested:

Nested objects
====================

Nested objects are supported out of the box. It is surprising, but you do not have to do anything except defining your dataclasses.
For example, your expect that author of Book is instance of Person, but in serialzied form it is dictionary.

Declare your dataclasses as usual and then just parse your data.

.. literalinclude:: examples/nested.py


Lists and other collections
============================

Want to parse collection of dataclasses? No changes required, just specify correct target type (e.g ``List[SomeClass]`` or ``Dict[str, SomeClass]``).

.. literalinclude:: examples/collection.py

Fields also can contain any supported collections.


Error handling
==================

Currently parser doesn't throw any specific exception in case of parser failes. Errors are the same as thrown by corresponding constructors.
In normal cases all suitable exceptions are described in ``dataclass_factory.PARSER_EXCEPTIONS``

.. literalinclude:: examples/errors.py

.. _validation:

Validation
===================

No validation patterns are provided currently. But anyway you can do any check in ``pre_parse`` or ``post_parse`` step.

``post_parse`` function is set for each type and does any additional work after parsing is done. It receives parsed data (instance of corresponding type). The result of ``post_parse`` function is used as a parsing result.

.. literalinclude:: examples/validation.py