from dataclasses import dataclass

from adaptix import Retort
from adaptix.load_error import TypeLoadError
from adaptix.struct_trail import ExcPathRenderer, PathedException


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
    }
}

retort = Retort()

try:
    with ExcPathRenderer():
        retort.load(data, Book)
except PathedException as e:
    assert isinstance(e.exc, TypeLoadError)
    assert list(e.path) == ['author', 'id']
    assert str(e) == "at ['author', 'id'] was raised TypeLoadError: expected_type=<class 'str'>"
