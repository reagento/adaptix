from dataclasses import dataclass
from typing import List

from dataclass_factory import Retort


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
books = retort.load(data, List[Book])
assert books == [Book(title="Fahrenheit 451", price=100), Book(title="1984", price=100)]
assert retort.dump(books, List[Book]) == data
