from dataclasses import dataclass

from adaptix import Retort
from adaptix.load_error import AggregateLoadError, LoadError


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    # Field values are mixed up
    "title": 100,
    "price": "Fahrenheit 451",
}

retort = Retort()

try:
    retort.load(data, Book)
except LoadError as e:
    assert isinstance(e, AggregateLoadError)
