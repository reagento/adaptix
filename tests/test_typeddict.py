import sys
from typing import Any
from unittest import TestCase, skipUnless
from itertools import product
from nose2.tools import params  # type: ignore
from typing_extensions import TypedDict as CompatTypedDict, Required as CompatRequired, NotRequired as CompatNotRequired
from dataclass_factory import Factory, NameStyle, Schema

TYPED_DICTS: Any = [CompatTypedDict]
REQUIRED: Any = [CompatRequired]  # type: ignore
NOT_REQUIRED: Any = [CompatNotRequired]  # type: ignore
if sys.version_info >= (3, 8):
    from typing import TypedDict as PyTypedDict
if sys.version_info >= (3, 11):
    from typing import Required, NotRequired
    REQUIRED.append(Required)  # type: ignore
    NOT_REQUIRED.append(NotRequired)  # type: ignore


class TestTypedDict(TestCase):
    @params(*TYPED_DICTS)
    def test_load(self, typed_dict):
        class Book(typed_dict):
            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello",
            "year": 1,
        }
        self.assertEqual(data, factory.load(data, Book))
        self.assertEqual(data, factory.dump(data, Book))

    @params(*TYPED_DICTS)
    def test_total(self, typed_dict):
        class Book(typed_dict, total=True):
            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello",
        }
        self.assertRaises((ValueError, KeyError), factory.load, data, Book)

    @params(*TYPED_DICTS)
    def test_not_total(self, typed_dict):
        class Book(typed_dict, total=False):

            name: str
            year: int

        factory = Factory()
        data = {
            "name": "hello",
        }
        self.assertEqual(data, factory.load(data, Book))
        self.assertEqual(data, factory.dump(data, Book))

    @params(*TYPED_DICTS)
    def test_complex(self, typed_dict):
        class MyDict(typed_dict, total=True):
            python_name: str
            other: str

        factory = Factory(default_schema=Schema(
            name_style=NameStyle.dot,
            name_mapping={"other": ("inner", "field")},
        ))
        data = {
            "python.name": "hello",
            "inner": {
                "field": "world",
            },
        }
        mydict: MyDict = dict(python_name="hello", other="world")
        self.assertEqual(mydict, factory.load(data, MyDict))
        self.assertEqual(data, factory.dump(mydict, MyDict))

    @skipUnless(sys.version_info >= (3, 9), "requires Python >= 3.9")
    @params(*TYPED_DICTS)
    def test_inheritance(self, typed_dict):
        class Parent(typed_dict, total=False):
            name: str

        class Child(Parent):
            age: int
        data = {
            "age": 10
        }
        factory = Factory()
        self.assertEqual(data, factory.load(data, Child))
        self.assertEqual(data, factory.dump(data, Child))

    @params(*product((CompatTypedDict,), REQUIRED))
    def test_required(self, typed_dict, required):
        class Book(typed_dict, total=False):
            name: required[str]
            year: int
        data = {
            "name": "hello"
        }
        factory = Factory()
        self.assertEqual(data, factory.load(data, Book))
        self.assertEqual(data, factory.dump(data, Book))

    @skipUnless(sys.version_info >= (3, 9), "requires Python >= 3.9")
    @params(*product((CompatTypedDict,), NOT_REQUIRED))
    def test_not_required(self, typed_dict, not_required):
        class Book(typed_dict):
            name: not_required[str]
            year: int
        data = {
            "year": 10
        }
        factory = Factory()
        self.assertEqual(data, factory.load(data, Book))
        self.assertEqual(data, factory.dump(data, Book))

    @params(*product((CompatTypedDict,), REQUIRED))
    def test_inheritance_required(self, typed_dict, required):
        class Parent(typed_dict):
            name: str

        class Child(Parent, total=False):
            age: required[int]

        data = {
            "name": "hello",
            "age": 10
        }
        factory = Factory()
        self.assertEqual(data, factory.load(data, Child))
        self.assertEqual(data, factory.dump(data, Child))

    @skipUnless(sys.version_info >= (3, 9), "requires Python >= 3.9")
    @params(*product((CompatTypedDict,), NOT_REQUIRED))
    def test_inheritance_not_required(self, typed_dict, not_required):
        class Parent(typed_dict, total=False):
            name: str

        class Child(Parent):
            age: not_required[int]

        data = {}
        factory = Factory()
        self.assertEqual(data, factory.load(data, Child))
        self.assertEqual(data, factory.dump(data, Child))

    @skipUnless((3, 8) <= sys.version_info <= (3, 10), "requires Python <= 3.10 and >= 3.8")
    @params(*product(REQUIRED, NOT_REQUIRED))
    def test_incorrect_inheritance_from_typing_td(self, required, not_required):
        class Parent(PyTypedDict, total=False):
            name: required[str]

        class Child(Parent):
            age: not_required[int]

        data = {
            "name": "hello"
        }
        factory = Factory()
        self.assertRaises(ValueError, factory.load, data, Child)
