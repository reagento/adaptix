from typing import TypedDict
from unittest import TestCase

from dataclass_factory import Factory


class Book(TypedDict):
    name: str
    year: int


class Author(TypedDict):
    author_name: str
    book: Book


class Author2(TypedDict):
    name: str
    book: Book


class TestTypedDict(TestCase):
    def test_load(self):
        factory = Factory()
        data = {
            "name": "hello",
            "year": 1
        }
        expected = Book(name="hello", year=1)
        self.assertEqual(expected, factory.load(data, Book))

    def test_load2(self):
        factory = Factory()
        data = {
            "author_name": "nobody",
            "book": {"name": "hello", "year": 1},
        }
        expected = Author(author_name="nobody", book=Book(name="hello", year=1))
        self.assertEqual(expected, factory.load(data, Author))

    def test_load3(self):
        factory = Factory()
        data = {
            "name": "nobody",
            "book": {"name": "hello", "year": 1},
        }
        expected = Author2(name="nobody", book=Book(name="hello", year=1))
        self.assertEqual(expected, factory.load(data, Author2))
