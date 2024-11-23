from pydantic import BaseModel

from adaptix import Retort


class Book(BaseModel):
    title: str
    price: int


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

retort = Retort()
book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == data
