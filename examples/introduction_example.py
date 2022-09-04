from dataclasses import dataclass

from dataclass_factory_30.facade import Factory


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
        "title": "Fahrenheit 451",
        "price": 100,
}


factory = Factory()
book = factory.parser(Book)(data)
print(book)
serialized = factory.serializer(Book)(book)
print(serialized)
