from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

retort = Retort()

book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == data
