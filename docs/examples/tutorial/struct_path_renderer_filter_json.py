import logging
from dataclasses import dataclass

from pythonjsonlogger import jsonlogger

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
logging.getLogger().handlers[0].formatter = jsonlogger.JsonFormatter()
# one line needed by adaptix
logging.getLogger().addFilter(StructPathRendererFilter())

retort = Retort()

try:
    retort.load(data, Book)
except LoadError as e:
    # {"message": "Bad input data for book", ..., "struct_path": ["author", "id"]}
    logging.warning("Bad input data for book", exc_info=e)
except Exception:
    logging.exception("Unexpected error at book loading")

# {"message": "some other message", ...}
logging.error('Some other message')
