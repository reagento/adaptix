from dataclasses import dataclass

from adaptix import Retort
from adaptix.load_error import LoadError, TypeLoadError
from adaptix.struct_path import get_path


@dataclass
class Person:
    id: str
    name: str


@dataclass
class Book:
    title: str
    price: int
    author: Person


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "author": {
        "id": 753,  # model declaration requires string!
        "name": "Ray Bradbury",
    },
}

retort = Retort()

try:
    retort.load(data, Book)
except LoadError as e:
    assert isinstance(e, TypeLoadError)
    assert e.expected_type == str
    assert list(get_path(e)) == ['author', 'id']
