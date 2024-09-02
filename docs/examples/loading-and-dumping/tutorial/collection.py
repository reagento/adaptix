from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Book:
    title: str
    price: int


data = [
    {
        "title": "Fahrenheit 451",
        "price": 100,
    },
    {
        "title": "1984",
        "price": 100,
    },
]

retort = Retort()
books = retort.load(data, list[Book])
assert books == [Book(title="Fahrenheit 451", price=100), Book(title="1984", price=100)]
assert retort.dump(books, list[Book]) == data
