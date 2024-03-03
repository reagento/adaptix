from dataclasses import dataclass
from datetime import date

from adaptix.conversion import get_converter


@dataclass
class Book:
    title: str
    price: int
    author: str
    release_date: date
    page_count: int
    isbn: str


@dataclass
class BookDTO:
    title: str
    price: int
    author: str


convert_book_to_dto = get_converter(Book, BookDTO)

assert (
    convert_book_to_dto(
        Book(
            title="Fahrenheit 451",
            price=100,
            author="Ray Bradbury",
            release_date=date(1953, 10, 19),
            page_count=158,
            isbn="978-0-7432-4722-1",
        ),
    )
    ==
    BookDTO(
        title="Fahrenheit 451",
        price=100,
        author="Ray Bradbury",
    )
)
