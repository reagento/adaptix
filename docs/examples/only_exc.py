from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int
    extra: str = ""


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "extra": "some extra string"
}

# using `only`:
factory = dataclass_factory.Factory(schemas={Book: Schema(only=["title", "price"])})
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)  # no `extra` key will be in serialized

# using `exclude`
factory = dataclass_factory.Factory(schemas={Book: Schema(exclude=["extra"])})
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)  # no `extra` key will be in serialized
