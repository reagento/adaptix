from dataclasses import dataclass

from dataclass_factory import P, Retort, validator
from dataclass_factory.load_error import LoadError, ValidationError


@dataclass
class Book:
    title: str
    price: int


data = {
    "title": "Fahrenheit 451",
    "price": -10,
}

retort = Retort(
    recipe=[
        validator(P[Book].price, lambda x: x >= 0, "value must be greater or equal 0"),
    ],
)

try:
    retort.load(data, Book)
except ValidationError as e:
    assert e.msg == "value must be greater or equal 0"


class BelowZero(LoadError):
    pass


retort = Retort(
    recipe=[
        validator(P[Book].price, lambda x: x >= 0, lambda x: BelowZero()),
    ],
)

try:
    retort.load(data, Book)
except BelowZero:
    pass
