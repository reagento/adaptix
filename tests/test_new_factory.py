from dataclasses import dataclass
from unittest import TestCase

from datetime import datetime

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


book_schema = Schema(
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
            Author("Petr", datetime(1970, 1, 2, 3, 4, 56)),
            "Book1",
            100,
        )
        expected = {
            'Title': 'Book1',
            'AuthorInfo': {'born_at': 86696, 'name': 'Petr'}
        }
        serialized = factory.dump(book)
        self.assertEqual(expected, serialized)

        parsed = factory.load(serialized, Book)
        self.assertEqual(parsed._price, 0)
        self.assertEqual(parsed.author_info, book.author_info)
        self.assertEqual(parsed.title, book.title)
