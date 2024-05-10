from dataclasses import dataclass
from datetime import date
from uuid import UUID

from adaptix.conversion import ConversionRetort, coercer


@dataclass
class Book:
    id: UUID
    title: str
    release_at: date


@dataclass
class BookDTO:
    id: str
    title: str
    release_at: str


retort = ConversionRetort(
    recipe=[
        coercer(UUID, str, str),
        coercer(date, str, lambda x: x.strftime("%d.%m.%Y")),
    ],
)

convert_book_to_dto = retort.get_converter(Book, BookDTO)

assert (
    convert_book_to_dto(
        Book(
            id=UUID("87000388-94e6-49a4-b51b-320e38577bd9"),
            title="Fahrenheit 451",
            release_at=date(1953, 10, 19),
        ),
    )
    ==
    BookDTO(
        id="87000388-94e6-49a4-b51b-320e38577bd9",
        title="Fahrenheit 451",
        release_at="19.10.1953",
    )
)
