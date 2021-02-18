from dataclasses import dataclass
from typing import List, NewType
from unittest import TestCase

from dataclass_factory import Factory


Id = NewType("Id", int)


@dataclass
class Duck:
    id: Id
    ducklings: List["Duck"]


class TestNewtype(TestCase):
    def test_serialize(self):
        factory = Factory()
        duck = Duck(
            Id(0),
            [Duck(Id(1), []), Duck(Id(2), [])]
        )
        expected = {
            'id': 0,
            'ducklings': [
                {'id': 1, 'ducklings': []},
                {'id': 2, 'ducklings': []},
            ],
        }
        serialized = factory.dump(duck)
        self.assertEqual(expected, serialized)

    def test_parse(self):
        factory = Factory()
        serialized = {
            'id': 0,
            'ducklings': [
                {'id': 1, 'ducklings': []},
                {'id': 2, 'ducklings': []},
            ]
        }
        expected = Duck(
            Id(0),
            [Duck(Id(1), []), Duck(Id(2), [])]
        )
        parsed = factory.load(serialized, Duck)
        self.assertEqual(expected, parsed)
