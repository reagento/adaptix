from dataclasses import dataclass

from dataclass_factory_30.facade import Retort


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


def test_readme(accum):
    data = {
        "title": "Fahrenheit 451",
        "price": 100,
    }

    retort = Retort(recipe=[accum])
    book = retort.load(data, Book)
    assert book == Book(title="Fahrenheit 451", price=100)
    dumped = retort.dump(book)
    assert dumped == data
