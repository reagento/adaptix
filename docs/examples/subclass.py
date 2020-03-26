from typing import Any

from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: int
    _author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}


class DataSchema(Schema[Any]):
    skip_internal = True

    def post_parse(self, data):
        print("parsing done")
        return data


factory = dataclass_factory.Factory(schemas={Book: DataSchema(trim_trailing_underscore=False)})

book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)
