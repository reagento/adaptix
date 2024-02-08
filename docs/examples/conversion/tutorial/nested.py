from dataclasses import dataclass

from adaptix.conversion import get_converter


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


convert_book_to_dto = get_converter(Book, BookDTO)

assert (
    convert_book_to_dto(
        Book(title="Fahrenheit 451", price=100, author=Person("Ray Bradbury"))
    )
    ==
    BookDTO(title="Fahrenheit 451", price=100, author=PersonDTO("Ray Bradbury"))
)
