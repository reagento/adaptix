from pydantic import BaseModel, Field

from adaptix import Retort
from adaptix.integrations.pydantic import native_pydantic


class Book(BaseModel):
    title: str = Field(alias="name")
    price: int


data = {
    "name": "Fahrenheit 451",
    "price": 100,
}

retort = Retort(
    recipe=[
        native_pydantic(Book),
    ],
)

book = retort.load(data, Book)
assert book == Book(name="Fahrenheit 451", price=100)
assert retort.dump(book) == data
