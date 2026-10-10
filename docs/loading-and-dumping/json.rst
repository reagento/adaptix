JSON bytes and strings
======================

``JsonRetort`` composes a regular ``Retort`` with a JSON codec. It accepts
``str``, ``bytes`` and ``bytearray`` and returns ``bytes`` by default:

.. code-block:: python

   from dataclasses import dataclass

   from adaptix import CodeGenBackend, Retort
   from adaptix.json import JsonRetort

   @dataclass
   class Item:
       id: int
       name: str

   json_retort = JsonRetort(Retort(codegen_backend=CodeGenBackend.X86_64))
   load = json_retort.get_loader(Item)
   dump = json_retort.get_dumper(Item)

   item = load(b'{"id":1,"name":"example"}')
   assert dump(item) == b'{"id":1,"name":"example"}'
   assert json_retort.dump(item, Item, as_bytes=False) == '{"id":1,"name":"example"}'

Pass an existing configured ``Retort`` to preserve its recipes, field naming,
defaults, extra-field policies and error trails. Reuse ``get_loader`` and
``get_dumper`` results to exclude converter generation from repeated calls.
``get_dumper(Item, as_bytes=False)`` produces JSON strings directly.

The Python backend uses the standard-library JSON codec. The experimental
x86-64 backend generates native parsing and writing routines on Linux,
GIL-enabled CPython. It builds a collision-free lookup table for known converter
keys, verifies the key bytes before accepting a lookup, scans strings with SSE2,
and writes to a growing byte buffer. Unknown keys still follow the configured
Adaptix policy. Input field order and duplicate keys follow normal JSON decoding
behavior; the last duplicate wins.

For flat models with scalar loaders, the native parser reads fields directly
into local slots and constructs the model after validating the entire document.
Compatible model dumpers and list dumpers write JSON directly from their source
objects, using pre-encoded field names and specialized child routines. They avoid
intermediate dictionaries and converted lists. Attribute guards reject custom
descriptors without invoking them speculatively. Other converters retain the
two-stage path through Python containers.

Ordinary escapes are parsed and written natively; Unicode escape sequences use
CPython's string scanner. Small integers use a digit-pair table. Short decimal
floats use native arithmetic after an exact round-trip check; altered floating
point modes use the general formatter. When system ``libstdc++.so.6`` provides
a compatible ``std::to_chars``, other floats are formatted directly into the
output buffer. Its ABI and representative outputs are checked before use.
Without it, formatting uses CPython's round-trip routine. Float parsing avoids
intermediate Python byte tokens. Unusually large integers,
non-UTF-8 input encodings, deep nesting and unsupported native output types use
the standard-library codec. Native nesting has a separate stack budget, and
errors unwind before retrying. Fallbacks do not repeat constructor or custom
converter calls.

NaN and Infinity constants are rejected; non-finite output floats raise
``ValueError``. Other parsing behavior follows the standard-library decoder,
including exponent overflow and escaped lone surrogates. This differs from
some other JSON libraries. ``StdlibJsonCodec`` can be explicitly supplied as
``JsonRetort(retort, codec=StdlibJsonCodec())`` for comparison.

``benchmarks/benchmarks/bench_json_codegen.py`` compares the complete conversion
path against typed ``msgspec.json.Decoder`` and ``msgspec.json.Encoder``. It
includes Python and x86 object converters with the standard-library codec,
plus the generated JSON codec, for both byte and string input/output. Converter
creation is outside the timed operation. For string output the msgspec baseline
includes decoding the encoder's returned UTF-8 bytes.
