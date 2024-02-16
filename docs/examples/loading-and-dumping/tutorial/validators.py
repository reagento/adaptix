from dataclasses import dataclass

from adaptix import P, Retort, validator
from adaptix.load_error import AggregateLoadError, LoadError, ValidationLoadError


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
except AggregateLoadError as e:
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], ValidationLoadError)
    assert e.exceptions[0].msg == "value must be greater or equal 0"


class BelowZero(LoadError):
    def __init__(self, actual_value: int):
        self.actual_value = actual_value

    def __str__(self):
        return f'actual_value={self.actual_value}'


retort = Retort(
    recipe=[
        validator(P[Book].price, lambda x: x >= 0, lambda x: BelowZero(x)),
    ],
)

try:
    retort.load(data, Book)
except AggregateLoadError as e:
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], BelowZero)
    assert e.exceptions[0].actual_value == -10
