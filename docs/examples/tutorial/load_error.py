from dataclasses import dataclass

from adaptix import Retort
from adaptix.load_error import LoadError, NoRequiredFieldsError


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451"
}

retort = Retort()

try:
    retort.load(data, Book)
except LoadError as e:
    assert isinstance(e, NoRequiredFieldsError)
    assert e.fields == ['price']
