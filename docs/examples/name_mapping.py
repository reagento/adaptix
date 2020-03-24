from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int


data = {
    "title": "Fahrenheit 451",
    "book price": 100,
}

book_schema = Schema(name_mapping={
    "price": "book price"
})
factory = dataclass_factory.Factory(schemas={Book: book_schema})
book: Book = factory.load(data, Book)
serialized = factory.dump(book)
