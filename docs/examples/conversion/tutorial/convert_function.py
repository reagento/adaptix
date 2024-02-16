from dataclasses import dataclass

from adaptix.conversion import convert


@dataclass
class Person:
    name: str


@dataclass
class Book:
    title: str
    price: int
    author: Person


@dataclass
class PersonDTO:
    name: str


@dataclass
class BookDTO:
    title: str
    price: int
    author: PersonDTO


assert (
    convert(
        Book(title="Fahrenheit 451", price=100, author=Person("Ray Bradbury")),
        BookDTO,
    )
    ==
    BookDTO(title="Fahrenheit 451", price=100, author=PersonDTO("Ray Bradbury"))
)
