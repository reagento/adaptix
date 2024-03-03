from dataclasses import dataclass

from adaptix import Retort, name_mapping


@dataclass
class Book:
    title: str
    price: int
    author: str


retort = Retort(
    recipe=[
        name_mapping(
            Book,
            map=[
                ("author", (..., "name")),
                ("title|price", ("book", ...)),
            ],
        ),
    ],
)

data = {
    "book": {
        "title": "Fahrenheit 451",
        "price": 100,
    },
    "author": {
        "name": "Ray Bradbury",
    },
}
book = retort.load(data, Book)
assert book == Book(
    title="Fahrenheit 451",
    price=100,
    author="Ray Bradbury",
)
assert retort.dump(book) == data
