from dataclasses import dataclass
from timeit import timeit

from marshmallow import Schema, fields, post_load
from typing import List

from dataclass_factory import Factory, Schema as DSchema


@dataclass
class Todo:
    id: int
    title: str
    desc: str

# my
factory = Factory(schemas={
    Todo: DSchema(
        name_mapping={
            "desc": ("description", "qwerty", 0, 5, 6),
        }
    )
})
parser = factory.parser(List[Todo])

# test
todos = [{
    "description": {
        "qwerty": [
            [
                None,
                None,
                None,
                None,
                None,
                [
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "5some long description %s %s %s" % (i, i * 10, i)
                ]
            ]
        ],
    },
    "id": i,
    "title": "title %s" % i,
} for i in range(10)]


def do1():
    return parser(todos)


print("my   ", timeit("do()", globals={"do": do1}, number=100000))  # 1.1471970899983717
