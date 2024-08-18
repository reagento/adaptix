from dataclasses import dataclass
from typing import Any

from adaptix import NameStyle, Retort, name_mapping


@dataclass
class Person:
    first_name: str
    last_name: str
    extra: dict[str, Any]


@dataclass
class Book:
    title: str
    author: Person


retort = Retort(
    recipe=[
        name_mapping(Person, name_style=NameStyle.UPPER_SNAKE),
        name_mapping(Person, name_style=NameStyle.CAMEL),
        name_mapping("author", extra_in="extra", extra_out="extra"),
    ],
)

data = {
    "title": "Lord of Light",
    "author": {
        "FIRST_NAME": "Roger",
        "LAST_NAME": "Zelazny",
        "UNKNOWN_FIELD": 1995,
    },
}
book = retort.load(data, Book)
assert book == Book(
    title="Lord of Light",
    author=Person(
        first_name="Roger",
        last_name="Zelazny",
        extra={"UNKNOWN_FIELD": 1995},
    ),
)
assert retort.dump(book) == data
