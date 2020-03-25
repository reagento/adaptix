from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int
    author: str


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "author": {
        "name": "Ray Bradbury"
    }
}

book_schema = Schema(
    name_mapping={
        "author": ("author", "name")
    }
)
factory = dataclass_factory.Factory(schemas={Book: book_schema})

# Book(title="Fahrenheit 451", price=100, author="Ray Bradbury")
book: Book = factory.load(data, Book)
serialized = factory.dump(book)
assert serialized == data
