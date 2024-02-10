from dataclasses import dataclass
from uuid import UUID

from adaptix.conversion import coercer, get_converter


@dataclass
class Book:
    id: UUID
    title: str
    author: str


@dataclass
class BookDTO:
    id: str
    title: str
    author: str


convert_book_to_dto = get_converter(
    src=Book,
    dst=BookDTO,
    recipe=[coercer(UUID, str, func=str)],
)

assert (
    convert_book_to_dto(
        Book(
            id=UUID('87000388-94e6-49a4-b51b-320e38577bd9'),
            title="Fahrenheit 451",
            author="Ray Bradbury",
        )
    )
    ==
    BookDTO(
        id='87000388-94e6-49a4-b51b-320e38577bd9',
        title="Fahrenheit 451",
        author="Ray Bradbury",
    )
)
