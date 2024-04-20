from pydantic import BaseModel

from adaptix import Retort, name_mapping


class Book(BaseModel):
    title: str
    price: int
    _private: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._private = 1


retort = Retort(
    recipe=[
        name_mapping(Book, map={"_private": "private_field"}),
    ],
)
book = Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == {
    "title": "Fahrenheit 451",
    "price": 100,
    "private_field": 1,
}
