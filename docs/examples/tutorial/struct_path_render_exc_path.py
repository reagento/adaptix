from dataclasses import dataclass

from dataclass_factory import Retort
from dataclass_factory.load_error import TypeLoadError
from dataclass_factory.struct_path import PathedException, render_exc_path


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
    with render_exc_path:
        retort.load(data, Book)
except PathedException as e:
    assert isinstance(e.exc, TypeLoadError)
    assert list(e.path) == ['author', 'id']
    assert str(e) == "at ['author', 'id'] was raised TypeLoadError: <class 'str'>"
