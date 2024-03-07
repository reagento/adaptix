from dataclasses import dataclass
from decimal import Decimal

from adaptix import P
from adaptix.conversion import get_converter, link


@dataclass
class Book:
    name: str
    price: int  # same as BookDTO.cost
    author: str


@dataclass
class BookDTO:
    name: str
    cost: Decimal  # same as Book.price
    author: str


convert_book_to_dto = get_converter(
    src=Book,
    dst=BookDTO,
    recipe=[link(P[Book].price, P[BookDTO].cost, coercer=lambda x: Decimal(x) / 100)],
)

assert (
    convert_book_to_dto(Book(name="Fahrenheit 451", price=100, author="Ray Bradbury"))
    ==
    BookDTO(name="Fahrenheit 451", cost=Decimal("1"), author="Ray Bradbury")
)
