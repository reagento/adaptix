import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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


book_fields = {fld.name for fld in dataclasses.fields(Book)}


def attr_extractor(model: Book) -> Mapping[str, Any]:
    return {
        key: value
        for key, value in vars(model).items()
        if key not in book_fields
    }


retort = Retort(
    recipe=[
        name_mapping(Book, extra_in=attr_saturator, extra_out=attr_extractor),
    ],
)

book = retort.load(data, Book)
assert retort.dump(book) == data
