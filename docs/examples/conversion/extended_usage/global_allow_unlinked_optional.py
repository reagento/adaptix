from dataclasses import dataclass, field
from typing import List, Optional

from adaptix.conversion import allow_unlinked_optional, get_converter


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
    collection_id: Optional[int] = None
    bookmarks_ids: List[str] = field(default_factory=list)


convert_book_to_dto = get_converter(
    Book,
    BookDTO,
    recipe=[
        allow_unlinked_optional(),
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
