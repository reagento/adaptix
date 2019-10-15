try:
    from typing import TypedDict  # mypy: ignore
except ImportError:
    try:
        from mypy_extensions import TypedDict
    except ImportError:
        TypedDict = object

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
        if TypedDict is not object:
            factory = Factory()
            data = {
                "name": "hello",
                "year": 1
            }
            expected = Book(name="hello", year=1)
            self.assertEqual(expected, factory.load(data, Book))
        else:
            self.skipTest("TypedDict is unsupported")

    def test_load2(self):
        if TypedDict is not object:
            factory = Factory()
            data = {
                "author_name": "nobody",
                "book": {"name": "hello", "year": 1},
            }
            expected = Author(author_name="nobody", book=Book(name="hello", year=1))
            self.assertEqual(expected, factory.load(data, Author))
        else:
            self.skipTest("TypedDict is unsupported")

    def test_load3(self):
        if TypedDict is not object:
            factory = Factory()
            data = {
                "name": "nobody",
                "book": {"name": "hello", "year": 1},
            }
            expected = Author2(name="nobody", book=Book(name="hello", year=1))
            self.assertEqual(expected, factory.load(data, Author2))
        else:
            self.skipTest("TypedDict is unsupported")
