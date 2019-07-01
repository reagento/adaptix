from dataclasses import dataclass
from unittest import TestCase

from datetime import datetime, timezone

from dataclass_factory import Factory, Schema, NameStyle
from dataclass_factory.schema_helpers import unixtime_schema


@dataclass
class Author:
    name: str
    born_at: datetime


@dataclass
class Book:
    author_info: Author
    title: str
    _price: int = 0


book_schema = Schema[Book](
    name_style=NameStyle.camel
)


class TestFactory(TestCase):
    def test_create(self):
        factory = Factory(
            schemas={
                Book: book_schema,
                datetime: unixtime_schema,
            }
        )
        book = Book(
            Author("Petr", datetime(1970, 1, 2, 3, 4, 56, tzinfo=timezone.utc)),
            "Book1",
            100,
        )
        expected = {
            'Title': 'Book1',
            'AuthorInfo': {'born_at': 97496, 'name': 'Petr'}
        }
        serialized = factory.dump(book)
        self.assertEqual(expected, serialized)
