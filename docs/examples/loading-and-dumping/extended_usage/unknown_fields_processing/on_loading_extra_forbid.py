from dataclasses import dataclass

from adaptix import ExtraForbid, Retort, name_mapping
from adaptix.load_error import AggregateLoadError, ExtraFieldsLoadError


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

retort = Retort(
    recipe=[
        name_mapping(Book, extra_in=ExtraForbid()),
    ],
)

try:
    retort.load(data, Book)
except AggregateLoadError as e:
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], ExtraFieldsLoadError)
    assert set(e.exceptions[0].fields) == {"unknown1", "unknown2"}
