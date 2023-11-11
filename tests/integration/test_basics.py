from dataclasses import dataclass
from typing import Any, TypedDict

import pytest
from tests_helpers import raises_exc

from adaptix import DebugTrail, Retort
from adaptix.load_error import AggregateLoadError, TypeLoadError
from adaptix.struct_trail import extend_trail, get_trail


@dataclass
class ExampleAny:
    field1: Any
    field2: Any


def test_any(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(ExampleAny)
    assert loader({'field1': 1, 'field2': 1}) == ExampleAny(field1=1, field2=1)

    dumper = retort.get_dumper(ExampleAny)
    assert dumper(ExampleAny(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


@dataclass
class ExampleObject:
    field1: object
    field2: object


def test_object(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(ExampleObject)
    assert loader({'field1': 1, 'field2': 1}) == ExampleObject(field1=1, field2=1)

    dumper = retort.get_dumper(ExampleObject)
    assert dumper(ExampleObject(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


@dataclass
class ExampleInt:
    field1: int
    field2: int


def test_int(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    raises_exc(
        AggregateLoadError(
            f'while loading model {ExampleInt}',
            [
                extend_trail(
                    TypeLoadError(int, '1'),
                    ['field2'],
                )
            ]
        ),
        lambda: loader({'field1': 1, 'field2': '1'})
    )

    dumper = retort.get_dumper(ExampleInt)
    assert dumper(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}


def test_int_lax_coercion(accum):
    retort = Retort(recipe=[accum], strict_coercion=False)
    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)
    assert loader({'field1': 1, 'field2': '1'}) == ExampleInt(field1=1, field2=1)


def test_int_dt_disable(accum):
    retort = Retort(recipe=[accum], debug_trail=DebugTrail.DISABLE)
    loader = retort.get_loader(ExampleInt)

    assert loader({'field1': 1, 'field2': 1}) == ExampleInt(field1=1, field2=1)

    with pytest.raises(TypeLoadError) as exc_info:
        loader({'field1': 1, 'field2': '1'})

    assert list(get_trail(exc_info.value)) == []

    dumper = retort.get_dumper(ExampleInt)
    assert dumper(ExampleInt(field1=1, field2=1)) == {'field1': 1, 'field2': 1}
