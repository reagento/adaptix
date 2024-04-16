# mypy: disable-error-code="empty-body"
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from adaptix import P
from adaptix.conversion import coercer, from_param, impl_converter, link


@dataclass
class Author:
    name: str
    surname: str
    birthday: date  # is converted to str


@dataclass
class Book:
    id: UUID  # is converted to str
    title: str
    author: Author  # is renamed to `writer`
    isbn: str  # this field is ignored


@dataclass
class AuthorDTO:
    name: str
    surname: str
    birthday: str


@dataclass
class BookDTO:
    id: str
    title: str
    writer: AuthorDTO
    page_count: int  # is taken from `pages_len` param
    rating: float  # is taken from param with the same name


@impl_converter(
    recipe=[
        link(from_param("pages_len"), P[BookDTO].page_count),
        link(P[Book].author, P[BookDTO].writer),
        coercer(UUID, str, func=str),
        coercer(P[Author].birthday, P[AuthorDTO].birthday, date.isoformat),
    ],
)
def convert_book_to_dto(book: Book, pages_len: int, rating: float) -> BookDTO:
    ...


assert (
    convert_book_to_dto(
        book=Book(
            id=UUID("87000388-94e6-49a4-b51b-320e38577bd9"),
            isbn="978-0-7432-4722-1",
            title="Fahrenheit 451",
            author=Author(name="Ray", surname="Bradbury", birthday=date(1920, 7, 22)),
        ),
        pages_len=158,
        rating=4.8,
    )
    ==
    BookDTO(
        id="87000388-94e6-49a4-b51b-320e38577bd9",
        title="Fahrenheit 451",
        writer=AuthorDTO(name="Ray", surname="Bradbury", birthday="1920-07-22"),
        page_count=158,
        rating=4.8,
    )
)
