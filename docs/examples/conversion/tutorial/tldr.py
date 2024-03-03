from dataclasses import dataclass

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from adaptix.conversion import get_converter


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    price: Mapped[int]


@dataclass
class BookDTO:
    id: int
    title: str
    price: int


convert_book_to_dto = get_converter(Book, BookDTO)

assert (
    convert_book_to_dto(Book(id=183, title="Fahrenheit 451", price=100))
    ==
    BookDTO(id=183, title="Fahrenheit 451", price=100)
)
