from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int
    _total: int = 0


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "_total": 1000,
}

factory = dataclass_factory.Factory(default_schema=Schema(skip_internal=True))
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)  # no `_total` key will be produced

