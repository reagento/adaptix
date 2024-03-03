from dataclasses import dataclass
from typing import Any, Mapping

from adaptix import Retort, name_mapping


@dataclass
class Book:
    title: str
    price: int


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "unknown1": 1,
    "unknown2": 2,
}


def attr_saturator(model: Book, extra_data: Mapping[str, Any]) -> None:
    for key, value in extra_data.items():
        setattr(model, key, value)


retort = Retort(
    recipe=[
        name_mapping(Book, extra_in=attr_saturator),
    ],
)

book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100)
assert book.unknown1 == 1  # type: ignore[attr-defined]
assert book.unknown2 == 2  # type: ignore[attr-defined]
