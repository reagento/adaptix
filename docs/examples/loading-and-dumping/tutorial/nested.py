from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Person:
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
        "name": "Ray Bradbury",
    },
}

retort = Retort()

book: Book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100, author=Person("Ray Bradbury"))
assert retort.dump(book) == data
