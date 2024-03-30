# mypy: disable-error-code="empty-body"
from dataclasses import dataclass

from adaptix import P
from adaptix.conversion import from_param, impl_converter, link


@dataclass
class Person:
    name: str


@dataclass
class Book:
    title: str
    author: Person


@dataclass
class PersonDTO:
    name: str
    rating: float


@dataclass
class BookDTO:
    title: str
    author: PersonDTO


@impl_converter(recipe=[link(from_param("author_rating"), P[PersonDTO].rating)])
def convert_book_to_dto(book: Book, author_rating: float) -> BookDTO:
    ...


assert (
    convert_book_to_dto(
        Book(title="Fahrenheit 451", author=Person("Ray Bradbury")),
        4.8,
    )
    ==
    BookDTO(title="Fahrenheit 451", author=PersonDTO("Ray Bradbury", 4.8))
)
