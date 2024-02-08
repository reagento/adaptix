from dataclasses import dataclass

from adaptix.conversion import get_converter


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


@dataclass
class BookDTO:
    title: str
    price: int
    author: str


convert_book_to_dto = get_converter(Book, BookDTO)

assert (
    convert_book_to_dto(Book(title="Fahrenheit 451", price=100))
    ==
    BookDTO(title="Fahrenheit 451", price=100, author="Unknown author")
)
