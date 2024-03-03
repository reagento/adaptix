from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from adaptix import P, Retort, loader


@dataclass
class Person:
    id: int
    name: str
    created_at: datetime


@dataclass
class Book:
    name: str
    price: int
    created_at: datetime


@dataclass
class Bookshop:
    workers: List[Person]
    books: List[Book]


data = {
    "workers": [
        {
            "id": 193,
            "name": "Kate",
            "created_at": "2023-01-29T21:26:28.026860+00:00",
        },
    ],
    "books": [
        {
            "name": "Fahrenheit 451",
            "price": 100,
            "created_at": 1674938508.599962,
        },
    ],
}

retort = Retort(
    recipe=[
        loader(P[Book].created_at, lambda x: datetime.fromtimestamp(x, tz=timezone.utc)),
    ],
)

bookshop = retort.load(data, Bookshop)

assert bookshop == Bookshop(
    workers=[
        Person(
            id=193,
            name="Kate",
            created_at=datetime(2023, 1, 29, 21, 26, 28, 26860, tzinfo=timezone.utc),
        ),
    ],
    books=[
        Book(
            name="Fahrenheit 451",
            price=100,
            created_at=datetime(2023, 1, 28, 20, 41, 48, 599962, tzinfo=timezone.utc),
        ),
    ],
)
