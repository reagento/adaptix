from dataclasses import dataclass

import dataclass_factory


@dataclass
class Person:
    name: str


@dataclass
class Book:
    title: str
    price: int
    author: Person


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "author": {
        "name": "Ray Bradbury"
    }
}

factory = dataclass_factory.Factory()

# Book(title="Fahrenheit 451", price=100, author=Person("Ray Bradbury"))
book: Book = factory.load(data, Book)
serialized = factory.dump(book)
