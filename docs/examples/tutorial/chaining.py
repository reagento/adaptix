import json
from dataclasses import dataclass
from datetime import datetime

from dataclass_factory import Chain, P, Retort, dumper, loader


@dataclass
class Book:
    title: str
    price: int
    author: str


@dataclass
class Message:
    id: str
    timestamp: datetime
    body: Book


data = {
    "id": "ajsVre",
    "timestamp": '2023-01-29T21:26:28.026860',
    "body": '{"title": "Fahrenheit 451", "price": 100, "author": "Ray Bradbury"}'
}

retort = Retort(
    recipe=[
        loader(P[Message].body, json.loads, Chain.FIRST),
        dumper(P[Message].body, json.dumps, Chain.LAST),
    ],
)

message = retort.load(data, Message)
assert message == Message(
    id="ajsVre",
    timestamp=datetime(2023, 1, 29, 21, 26, 28, 26860),
    body=Book(
        title="Fahrenheit 451",
        price=100,
        author="Ray Bradbury",
    ),
)
