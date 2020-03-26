from typing import Optional, List

from dataclasses import dataclass, field

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Book:
    title: str
    price: Optional[int] = None
    authors: List[str] = field(default_factory=list)


data = {
    "title": "Fahrenheit 451",
}

factory = dataclass_factory.Factory(default_schema=Schema(omit_default=True))
book = Book(title="Fahrenheit 451", price=None, authors=[])
serialized = factory.dump(book)  # no `price` and `authors` key will be produced
assert data == serialized
