from dataclasses import dataclass
from datetime import datetime

from adaptix import Retort, loader
from adaptix.struct_trail import Attr, get_trail


@dataclass
class Book:
    title: str
    price: int
    created_at: datetime


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "created_at": '2023-10-07T16:25:19.303579',
}


def broken_title_loader(data):
    raise ArithmeticError('Some unexpected error')


retort = Retort(
    recipe=[
        loader('title', broken_title_loader),
    ],
)

try:
    retort.load(data, Book)
except Exception as e:
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], ArithmeticError)
    assert list(get_trail(e.exceptions[0])) == ['title']

book = Book(
    title="Fahrenheit 451",
    price=100,
    created_at=None,  # type: ignore[arg-type]
)

try:
    retort.dump(book)
except Exception as e:
    assert isinstance(e, ExceptionGroup)
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], TypeError)
    assert list(get_trail(e.exceptions[0])) == [Attr('created_at')]
