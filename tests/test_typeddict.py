import sys
from typing import Any
from unittest import TestCase

from nose2.tools import params  # type: ignore
from typing_extensions import TypedDict as CompatTypedDict

from dataclass_factory import Factory

TYPED_DICTS: Any = [CompatTypedDict]
if sys.version_info >= (3, 8):
    from typing import TypedDict as PyTypedDict

    TYPED_DICTS.append(PyTypedDict)


class TestTypedDict(TestCase):
    @params(*TYPED_DICTS)
    def test_load(self, typed_dict):
        class Book(typed_dict):
            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello",
            "year": 1
        }
        expected = dict(name="hello", year=1)
        self.assertEqual(expected, factory.load(data, Book))

    @params(*TYPED_DICTS)
    def test_total(self, typed_dict):
        class Book(typed_dict, total=True):
            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello"
        }
        self.assertRaises((ValueError, KeyError), factory.load, data, Book)

    @params(*TYPED_DICTS)
    def test_not_total(self, typed_dict):
        class Book(typed_dict, total=False):
            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello"
        }
        expected = dict(name="hello")
        self.assertEqual(expected, factory.load(data, Book))
