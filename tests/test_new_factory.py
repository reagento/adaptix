from dataclasses import dataclass
from datetime import datetime
from unittest import TestCase

from dataclass_factory import Factory, Schema, NameStyle
from dataclass_factory.schema_helpers import isotime_schema


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
                datetime: isotime_schema,
            }
        )
        book = Book(
            Author("Petr", datetime(1999, 1, 2, 9, 45, 56)),
            "Book1",
            100,
        )
        expected = {
            'Title': 'Book1',
            'AuthorInfo': {'born_at': '1999-01-02T09:45:56', 'name': 'Petr'}
        }
        serialized = factory.dump(book)
        self.assertEqual(expected, serialized)

        parsed = factory.load(serialized, Book)
        self.assertEqual(parsed._price, 0)
        self.assertEqual(parsed.author_info, book.author_info)
        self.assertEqual(parsed.title, book.title)
