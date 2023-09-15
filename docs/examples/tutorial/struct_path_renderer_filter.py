import logging
from dataclasses import dataclass

from adaptix import Retort
from adaptix.load_error import LoadError
from adaptix.struct_trail import StructPathRendererFilter


@dataclass
class Person:
    id: str
    name: str


@dataclass
class Book:
    title: str
    price: int
    author: Person


data = {
    "title": "Fahrenheit 451",
    "price": 100,
    "author": {
        "id": 753,  # model declaration requires string!
        "name": "Ray Bradbury",
    }
}

logging.basicConfig()
logging.getLogger().addFilter(StructPathRendererFilter())
logging.getLogger().handlers[0].formatter = logging.Formatter(
    fmt='{levelname}:{name}:{message} struct_path={struct_path}',
    style='{',
    defaults={'struct_path': None},
)

retort = Retort()

try:
    retort.load(data, Book)
except LoadError as e:
    # WARNING:root:Bad input data for book struct_path=['author', 'id']
    logging.warning("Bad input data for book", exc_info=e)
except Exception:
    logging.exception("Unexpected error at book loading")

# ERROR:root:some other message struct_path=None
logging.error('Some other message')
