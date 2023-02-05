from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class A:
    value: int


@dataclass
class Book:
    price: int


@dataclass
class Bookshelf:
    magazines: list
    books: list[Book]


class Test1(TestCase):
    def test_list(self):
        factory = Factory()
        self.assertEqual(factory.dump([A(1)]), [{"value": 1}])

    def test_dict(self):
        factory = Factory()
        self.assertEqual(factory.dump({"a": A(1)}), {"a": {"value": 1}})

    def test_generic_unspecified_args(self):
        # see https://github.com/reagento/dataclass-factory/issues/207 for
        # more information
        factory = Factory()
        data = {
            "magazines": [],
            "books": [{
                "price": 100
            }]
        }
        loaded = factory.load(data, Bookshelf)
        self.assertEqual(loaded, Bookshelf(
            magazines=[],
            books=[
                Book(price=100)
            ]
        ))
        self.assertEqual(factory.dump(loaded), data)
