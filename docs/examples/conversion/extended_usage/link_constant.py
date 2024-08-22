from dataclasses import dataclass
from typing import Optional

from adaptix import P
from adaptix.conversion import get_converter, link_constant


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
    collection_id: Optional[int]
    bookmarks_ids: list[str]


convert_book_to_dto = get_converter(
    Book,
    BookDTO,
    recipe=[
        link_constant(P[BookDTO].collection_id, value=None),
        link_constant(P[BookDTO].bookmarks_ids, factory=list),
    ],
)

assert (
    convert_book_to_dto(
        Book(
            title="Fahrenheit 451",
            price=100,
            author="Ray Bradbury",
        ),
    )
    ==
    BookDTO(
        title="Fahrenheit 451",
        price=100,
        author="Ray Bradbury",
        collection_id=None,
        bookmarks_ids=[],
    )
)
