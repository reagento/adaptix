from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from adaptix import Retort, name_mapping


@dataclass
class Book:
    title: str
    price: int
    extra: Mapping[str, Any]


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "unknown1": 1,
    "unknown2": 2,
}

retort = Retort(
    recipe=[
        name_mapping(Book, extra_in="extra", extra_out="extra"),
    ],
)

book = retort.load(data, Book)
assert book == Book(
    title="Fahrenheit 451",
    price=100,
    extra={
        "unknown1": 1,
        "unknown2": 2,
    },
)
assert retort.dump(book) == data
