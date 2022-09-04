from dataclasses import dataclass
from typing import Any

from dataclass_factory_30.facade import Factory


@dataclass
class ExampleAny:
    field1: Any
    field2: Any


factory = Factory()
parser = factory.parser(ExampleAny)
serializer = factory.serializer(ExampleAny)
simple_parsed = parser({"field1": 1, "field2": 1})
print(simple_parsed)
simple_serialized = serializer(simple_parsed)
print(simple_serialized)


@dataclass
class ExampleInt:
    field1: int
    field2: int


simple_int_parsed = parser({"field1": 1, "field2": 1})
print(simple_int_parsed)
simple_serialized = serializer(simple_int_parsed)
print(simple_int_parsed)


factory_without_lax_coercion = Factory(strict_coercion=False)
parser = factory_without_lax_coercion.parser(ExampleInt)
simple_int_parsed = parser({"field1": 1, "field2": "2"})
print(simple_int_parsed)
