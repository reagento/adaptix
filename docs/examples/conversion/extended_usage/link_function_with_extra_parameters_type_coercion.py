# mypy: disable-error-code="empty-body"
from dataclasses import dataclass
from datetime import date

from adaptix import P
from adaptix.conversion import coercer, impl_converter, link_function


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


def make_label(book: Book, released_at: str) -> str:
    return f"{book.title}. {book.sub_title} ({released_at})"


def format_date(x: date) -> str:
    return x.strftime("%d.%m.%Y")


@impl_converter(
    recipe=[
        link_function(make_label, P[BookDTO].label),
        coercer(date, str, format_date),
    ],
)
def convert_book_to_dto(book: Book, released_at: date) -> BookDTO:
    ...


assert (
    convert_book_to_dto(
        Book(
            title="Enchiridion",
            sub_title="Handbook of Epictetus",
            price=100,
            author="Arrian",
        ),
        released_at=date(year=1683, month=1, day=1),
    )
    ==
    BookDTO(
        label="Enchiridion. Handbook of Epictetus (01.01.1683)",
        price=100,
        author="Arrian",
    )
)
