from dataclasses import dataclass
from typing import Any

import pytest

from dataclass_factory import Retort
from dataclass_factory.load_error import TypeLoadError
from dataclass_factory.struct_path import get_path


@dataclass
class ExampleAny:
    field1: Any
    field2: Any


def test_simple(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(ExampleAny)
    assert loader({'field1': 1, 'field2': 1}) == ExampleAny(field1=1, field2=1)

    dumper = retort.get_dumper(ExampleAny)
    assert dumper(ExampleAny(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


@dataclass
class ExampleInt:
    field1: int
    field2: int


def test_simple_int(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    with pytest.raises(TypeLoadError) as exc_info:
        loader({'field1': 1, 'field2': '1'})

    assert list(get_path(exc_info.value)) == ['field2']

    dumper = retort.get_dumper(ExampleInt)
    assert dumper(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


def test_simple_int_lax_coercion(accum):
    retort = Retort(recipe=[accum], strict_coercion=False)
    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)
    assert loader({'field1': 1, 'field2': '1'}) == ExampleInt(field1=1, field2=1)


def test_simple_int_no_debug_path(accum):
    retort = Retort(recipe=[accum], debug_path=False)
    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    with pytest.raises(TypeLoadError) as exc_info:
        loader({'field1': 1, 'field2': '1'})

    assert list(get_path(exc_info.value)) == []

    dumper = retort.get_dumper(ExampleInt)
    assert dumper(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}
