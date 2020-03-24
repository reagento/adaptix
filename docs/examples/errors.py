from dataclasses import dataclass

import dataclass_factory


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451"
}

factory = dataclass_factory.Factory()

try:
    book: Book = factory.load(data, Book)
except dataclass_factory.PARSER_EXCEPTIONS as e:
    # Cannot parse:  <class 'TypeError'> __init__() missing 1 required positional argument: 'price'
    print("Cannot parse: ", type(e), e)
