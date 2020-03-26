from typing import List

from dataclasses import dataclass

import dataclass_factory


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
    }
]

factory = dataclass_factory.Factory()
books = factory.load(data, List[Book])
serialized = factory.dump(books)
