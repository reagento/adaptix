from dataclasses import dataclass
import dataclass_factory


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

factory = dataclass_factory.Factory()
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)