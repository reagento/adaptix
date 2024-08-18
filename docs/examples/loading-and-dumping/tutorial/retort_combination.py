from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from adaptix import Retort, bound, dumper, enum_by_name, loader


class LiteraryGenre(Enum):
    DRAMA = 1
    FOLKLORE = 2
    POETRY = 3
    PROSE = 4


@dataclass
class LiteraryWork:
    id: int
    name: str
    genre: LiteraryGenre
    uploaded_at: datetime


literature_retort = Retort(
    recipe=[
        loader(datetime, lambda x: datetime.fromtimestamp(x, tz=timezone.utc)),
        dumper(datetime, lambda x: x.timestamp()),
        enum_by_name(LiteraryGenre),
    ],
)


# another module and another abstraction level

@dataclass
class Person:
    name: str
    works: list[LiteraryWork]


retort = Retort(
    recipe=[
        bound(LiteraryWork, literature_retort),
    ],
)

data = {
    "name": "Ray Bradbury",
    "works": [
        {
            "id": 7397,
            "name": "Fahrenheit 451",
            "genre": "PROSE",
            "uploaded_at": 1675111113,
        },
    ],
}

person = retort.load(data, Person)
assert person == Person(
    name="Ray Bradbury",
    works=[
        LiteraryWork(
            id=7397,
            name="Fahrenheit 451",
            genre=LiteraryGenre.PROSE,
            uploaded_at=datetime(2023, 1, 30, 20, 38, 33, tzinfo=timezone.utc),
        ),
    ],
)
