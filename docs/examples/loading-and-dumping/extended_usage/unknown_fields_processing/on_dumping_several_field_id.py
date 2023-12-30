from dataclasses import dataclass
from typing import Any, Mapping

from adaptix import Retort, name_mapping


@dataclass
class Book:
    title: str
    price: int
    extra1: Mapping[str, Any]
    extra2: Mapping[str, Any]


retort = Retort(
    recipe=[
        name_mapping(Book, extra_out=["extra1", "extra2"]),
    ]
)

book = Book(
    title="Fahrenheit 451",
    price=100,
    extra1={
        "unknown1": 1,
        "unknown2": 2,
    },
    extra2={
        "unknown3": 3,
        "unknown4": 4,
    },
)
assert retort.dump(book) == {
    "title": "Fahrenheit 451",
    "price": 100,
    "unknown1": 1,
    "unknown2": 2,
    "unknown3": 3,
    "unknown4": 4,
}
