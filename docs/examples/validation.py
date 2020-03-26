from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}
invalid_data = {
    "title": "1984",
    "price": -100,
}


def validate_book(book: Book) -> Book:
    if not book.title:
        raise ValueError("Empty title")
    if book.price <= 0:
        raise ValueError("InvalidPrice")
    return book


factory = dataclass_factory.Factory(schemas={Book: Schema(post_parse=validate_book)})
book = factory.load(data, Book)  # No error
other_book = factory.load(invalid_data, Book)  # ValueError: InvalidPrice
