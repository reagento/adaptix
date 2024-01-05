from dataclasses import dataclass
from typing import Any, Dict

from adaptix import NameStyle, Retort, name_mapping


@dataclass
class Person:
    first_name: str
    last_name: str
    extra: Dict[str, Any]


@dataclass
class Book:
    title: str
    author: Person


retort = Retort(
    recipe=[
        name_mapping(Person, name_style=NameStyle.CAMEL),
        name_mapping('author', extra_in='extra', extra_out='extra'),
    ]
)

data = {
    'title': 'Lord of Light',
    'author': {
        'firstName': 'Roger',
        'lastName': 'Zelazny',
        'unknown_field': 1995,
    },
}
book = retort.load(data, Book)
assert book == Book(
    title='Lord of Light',
    author=Person(
        first_name='Roger',
        last_name='Zelazny',
        extra={'unknown_field': 1995},
    ),
)
assert retort.dump(book) == data
