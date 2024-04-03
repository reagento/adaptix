from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Book:
    title: str
    price: int


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

# Retort is meant to be global constant or just one-time created
retort = Retort()

book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == data
