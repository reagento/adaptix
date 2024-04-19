from pydantic import BaseModel

from adaptix import Retort


class Book(BaseModel):
    title: str
    price: int
    _private: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._private = 1


retort = Retort()
book = Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == {
    "title": "Fahrenheit 451",
    "price": 100,
}
