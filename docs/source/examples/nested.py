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
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100, author=Person("Ray Bradbury"))
serialized = factory.dump(book)
