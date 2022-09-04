from dataclasses import dataclass

from dataclass_factory_30.facade import Factory


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

    factory = Factory(recipe=[accum])
    book = factory.parser(Book)(data)
    assert book == Book(title="Fahrenheit 451", price=100)
    serialized = factory.serializer(Book)(book)
    assert serialized == data
