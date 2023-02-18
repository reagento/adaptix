from dataclasses import dataclass

from adaptix import Retort, loader
from adaptix.struct_path import Attr, get_path


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
        "id": '2ce5bc44e1384d91ba6767a8013ae505',
        "name": "Ray Bradbury",
    },
}


def broken_title_loader(data):
    raise ArithmeticError('Some unexpected error')


retort = Retort(
    recipe=[
        loader('title', broken_title_loader),
    ]
)

try:
    retort.load(data, Book)
except Exception as e:
    assert isinstance(e, ArithmeticError)
    assert list(get_path(e)) == ['title']

book = Book(
    title="Fahrenheit 451",
    price=100,
    author=None,  # type: ignore[arg-type]
)

try:
    retort.dump(book)
except Exception as e:
    assert isinstance(e, AttributeError)
    assert list(get_path(e)) == [Attr('author'), Attr('id')]
