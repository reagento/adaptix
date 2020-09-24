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

Validation of data can be done in two cases:

* per-field validations
* whole structure validation

In first case you can use ``@validate`` decorator to check the data. Here are details:

* validator CAN be called before parsing field data (set ``pre=True``) or after it.
* field validators are applied after all name transformations. So use field name as it is called in your dataclass/etc
* validator CAN be applied to multiple fields. Just provide multiple names
* validator CAN be applied to any field separately. Just do not set any field name
* validator MUST return data if checks are succeeded. Data can be same as passed to it or anything else. Validator CAN change data
* field validators CANNOT be set in default schema

.. literalinclude:: examples/validators.py


If you want to check whole structure, your can any check in ``pre_parse`` or ``post_parse`` step.
Idea is the same:

* ``pre_parse`` is called before structure parsing is done (but even before data is flattened and names are processed).
* ``post_parse`` is called after successful parsing

.. literalinclude:: examples/total_validation.py
