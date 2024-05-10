from dataclasses import dataclass

from adaptix import P
from adaptix.conversion import get_converter, link_function


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


convert_book_to_dto = get_converter(
    Book,
    BookDTO,
    recipe=[
        link_function(lambda book: f"{book.title}. {book.sub_title}", P[BookDTO].label),
    ],
)

assert (
    convert_book_to_dto(
        Book(
            title="Enchiridion",
            sub_title="Handbook of Epictetus",
            price=100,
            author="Arrian",
        ),
    )
    ==
    BookDTO(
        label="Enchiridion. Handbook of Epictetus",
        price=100,
        author="Arrian",
    )
)
