# mypy: disable-error-code="empty-body"
from dataclasses import dataclass

from adaptix import P
from adaptix.conversion import impl_converter, link_function


@dataclass
class Book:
    title: str
    sub_title: str
    price: int
    author: str


@dataclass
class BookDTO:
    label: str
    price: int
    author: str


@impl_converter(
    recipe=[
        link_function(
            lambda book, page_count: (
                f"{book.title}. {book.sub_title} ({page_count} pages)"
            ),
            P[BookDTO].label,
        ),
    ],
)
def convert_book_to_dto(book: Book, page_count: int) -> BookDTO:
    ...


assert (
    convert_book_to_dto(
        Book(
            title="Enchiridion",
            sub_title="Handbook of Epictetus",
            price=100,
            author="Arrian",
        ),
        page_count=23,
    )
    ==
    BookDTO(
        label="Enchiridion. Handbook of Epictetus (23 pages)",
        price=100,
        author="Arrian",
    )
)
