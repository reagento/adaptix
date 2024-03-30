# mypy: disable-error-code="empty-body"
from dataclasses import dataclass

from adaptix.conversion import impl_converter


@dataclass
class Book:
    title: str
    price: int
    author: str


@dataclass
class BookDTO:
    title: str
    price: int
    author: str
    page_count: int


@impl_converter
def convert_book_to_dto(book: Book, page_count: int) -> BookDTO:
    ...


assert (
    convert_book_to_dto(
        book=Book(
            title="Fahrenheit 451",
            price=100,
            author="Ray Bradbury",
        ),
        page_count=158,
    )
    ==
    BookDTO(
        title="Fahrenheit 451",
        price=100,
        author="Ray Bradbury",
        page_count=158,
    )
)
