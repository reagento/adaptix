from collections import deque
from dataclasses import dataclass
from typing import Any

import pytest

from dataclass_factory_30.factory import Factory
from dataclass_factory_30.provider.definitions import TypeParseError


@dataclass
class ExampleAny:
    field1: Any
    field2: Any


def test_simple(accum):
    factory = Factory(recipe=[accum])

    parser = factory.parser(ExampleAny)
    assert parser({'field1': 1, 'field2': 1}) == ExampleAny(field1=1, field2=1)

    serializer = factory.serializer(ExampleAny)
    assert serializer(ExampleAny(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


@dataclass
class ExampleInt:
    field1: int
    field2: int


def test_simple_int(accum):
    factory = Factory(recipe=[accum])

    parser = factory.parser(ExampleInt)

    assert parser({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    with pytest.raises(TypeParseError) as exc_info:
        parser({'field1': 1, 'field2': '1'})

    assert exc_info.value.path == deque(['field2'])

    serializer = factory.serializer(ExampleInt)
    assert serializer(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


def test_simple_int_lax_coercion(accum):
    factory = Factory(recipe=[accum], strict_coercion=False)
    parser = factory.parser(ExampleInt)

    assert parser({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)
    assert parser({'field1': 1, 'field2': '1'}) == ExampleInt(field1=1, field2=1)


def test_simple_int_no_debug_path(accum):
    factory = Factory(recipe=[accum], debug_path=False)
    parser = factory.parser(ExampleInt)

    assert parser({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    with pytest.raises(TypeParseError) as exc_info:
        parser({'field1': 1, 'field2': '1'})

    assert exc_info.value.path == deque()

    serializer = factory.serializer(ExampleInt)
    assert serializer(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}
