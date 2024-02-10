from dataclasses import dataclass

from adaptix import P
from adaptix.conversion import bind, get_converter


@dataclass
class Book:
    name: str
    price: int
    author: str  # same as BookDTO.writer


@dataclass
class BookDTO:
    name: str
    price: int
    writer: str  # same as Book.author


convert_book_to_dto = get_converter(
    src=Book,
    dst=BookDTO,
    recipe=[bind(P[Book].author, P[BookDTO].writer)],
)

assert (
    convert_book_to_dto(Book(name="Fahrenheit 451", price=100, author="Ray Bradbury"))
    ==
    BookDTO(name="Fahrenheit 451", price=100, writer="Ray Bradbury")
)
