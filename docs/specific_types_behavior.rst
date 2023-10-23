*****************************
Specific types behavior
*****************************

Builtin loaders and dumpers designed to work well with JSON data processing.
If you are working with a different format, you may need to override the default behavior,
see :ref:`retort-recipe` for details.

Mostly predefined loaders accept value only a single type;
if it's a string, it strings in a single format.
You can disable the ``strict_coercion`` parameter of :class:`.Retort`
to allow all conversions that the corresponding constructor can perform.


Scalar types
==============


Basic types
'''''''''''''

Values of these types are loaded using their constructor.
If ``strict_coercion`` is enabled,
the loader will pass only values of appropriate types listed at the ``Allowed strict origins`` row.

.. list-table::
   :header-rows: 1

   * - Type
     - Allowed strict origins
     - Dumping to
   * - ``int``
     - ``int``
     - `no conversion`
   * - ``float``
     - ``float``, ``int``
     - `no conversion`
   * - ``str``
     - ``str``
     - `no conversion`
   * - ``bool``
     - ``bool``
     - `no conversion`
   * - ``Decimal``
     - ``str``, ``Decimal``
     - ``str``
   * - ``Fraction``
     - ``str``, ``Fraction``
     - ``str``
   * - ``complex``
     - ``str``, ``complex``
     - ``str``

Any
'''''''''

Value is passed as is, without any conversion.

None
'''''''''

Loader accepts only ``None``, dumper produces no conversion.

bytes-like
'''''''''''''''''''''''''''''''''''''
Exact list: ``bytes``, ``bytearray``, ``ByteString``.

Value is represented as base64 encoded string.

re.Pattern
''''''''''''

The loader accepts a string that will be compiled into a regex pattern.
Dumper extracts the original string from a compiled pattern.

Path-like
''''''''''''''''''''''

Exact list: ``PurePath``, ``Path``,
``PurePosixPath``, ``PosixPath``,
``PureWindowsPath``, ``WindowsPath``, ``PathLike[str]``.

Loader takes any string accepted by the constructor,
dumper serialize value via ``__fspath__`` method.

``PathLike[str]`` loader produces ``Path`` instance

IP addresses and networks
''''''''''''''''''''''''''''

Exact list: ``IPv4Address``, ``IPv6Address``,
``IPv4Network``, ``IPv6Network``,
``IPv4Interface``, ``IPv6Interface``,

Loader takes any string accepted by the constructor,
dumper serialize value via ``__str__`` method.

UUID
''''''''''''''''''''''

Loader takes any hex string accepted by the constructor,
dumper serialize value via ``__str__`` method.

date, time and datetime
'''''''''''''''''''''''''''

Value is represented as an isoformat string.

timedelta
'''''''''''''''''''''''''''

Loader accepts instance of ``int``, ``float`` or ``Decimal`` representing seconds,
dumper serialize value via ``total_seconds`` method.

Enum subclasses
'''''''''''''''''''''''

Enum members are represented by their value without any conversion.

Compound types
================

NewType
'''''''''''''''''

All ``NewType``'s are treated as origin types.

For example, if you create ``MyNewModel = NewType('MyNewModel', MyModel)``,
``MyNewModel`` will share loader, dumper and name_mapping with ``MyModel``.
This also applies to user-defined providers.

You can override providers only for ``NewType`` if you pass ``MyNewModel`` directly as a predicate.

Metadata types
''''''''''''''''''

The types such as ``Final``, ``Annotated``, ``ClassVar`` and ``InitVar`` are processed the same as wrapped types.

Literal
'''''''''''''''''

Loader accepts only values listed in ``Literal``.
If ``strict_coercion`` is enabled, the loader will distinguish equal ``bool`` and ``int`` instances,
otherwise, they will be considered as same values.
``Enum`` instances will be loaded via its loaders.

If the input value could be interpreted as several ``Literal`` members, the result will be undefined.

Dumper will return value without any processing excluding ``Enum`` instances,
they will be processed via the corresponding dumper.

Be careful when you use a ``0``, ``1``, ``False`` and ``True`` as ``Literal`` members.
Due to type hint caching ``Literal[0, 1]`` sometimes returns ``Literal[False, True]``.
It was fixed only at `Python 3.9.1 <https://docs.python.org/3/whatsnew/3.9.html#id4>`_.

Union
'''''''''''''''''

Loader calls loader of each union case
and returns a value of the first loader that does not raise :class:`~.load_error.LoadError`.
Therefore, for the correct operation of a union loader,
there must be no value that would be accepted by several union case loaders.

.. literalinclude:: examples/specific_types_behavior/union_case_overlapping.py

The return value in this example is undefined, it can be either a Cat instance or a Dog instance.
This problem could be solved if the model will contain a designator (tag) that can uniquely determine the type.

.. literalinclude:: examples/specific_types_behavior/union_with_designator.py

This example shows how to add a type designator to the model.
Be careful, this example does not work if :paramref:`.name_mapping.omit_default` is applied to tag field.

Be careful if one model is a superset of another model.
By default, all unknown fields are skipped, this does not allow distinct such models.

.. literalinclude:: examples/specific_types_behavior/union_model_supersets.py

This can be avoided by inserting a type designator like in the example above.
Processing of unknown fields could be customized via :paramref:`.name_mapping.extra_in`.

Dumper finds appropriate dumper using object type.
This means that it does not distinguish ``List[int]`` and ``List[str]``.
For objects of types that are not listed in the union,
but which are a subclass of some union case, the base class dumper is used.
If there are several parents, it will be the selected class that appears first in ``.mro()`` list.

Also, builtin dumper can not work
with union containing non-class type hints like ``Union[Literal['foo', 'bar'], int]``.

Iterable subclasses
'''''''''''''''''''''

If ``strict_coercion`` is enabled, the loader takes any iterable excluding ``str`` and ``Mapping``.
If ``strict_coercion`` is disabled, any iterable are accepted.

Dumper produces the same iterable with dumped elements.

If you require a dumper or loader for abstract type, a minimal suitable type will be used.
For example, if you need a dumper for type ``Iterable[int]``, retort will use ``tuple``.
So if a field with ``Iterable[int]`` type will contain ``List[int]``,
the list will be converted to a tuple while dumping.

Dict and Mapping
'''''''''''''''''''''

Loader accepts any other ``Mapping`` and makes ``dict`` instances.
Dumper also constructs dict with converted keys and values.

Models
''''''''''

Models are classes that have a predefined set of fields.
By default, models are loading from dict, with keys equal field names,
but this behavior could be precisely configured via :func:`.name_mapping` mechanism.
Also, the model could be loaded from the list.

Dumper works similarly and produces dict (or list).

Models that are supported out of the box:

- `dataclass <https://docs.python.org/3/library/dataclasses>`_
- `NamedTuple <https://docs.python.org/3/library/typing.html#typing.NamedTuple>`_
  (`namedtuple <https://docs.python.org/3/library/collections.html#collections.namedtuple>`_
  also is supported, but types of all fields will be ``Any``)
- `TypedDict <https://docs.python.org/3/library/typing.html#typing.TypedDict>`_
- `attrs <https://www.attrs.org/en/stable/>`_

Arbitrary types also are supported to be loaded by introspection of ``__init__`` method,
but it can not be dumped.
