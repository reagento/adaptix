import json
from copy import deepcopy
from dataclasses import dataclass, asdict
from timeit import timeit

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
            "title": ("smth", "qwerty", 0, 5, 6),
            "id": ("smth", "qwerty", 1),
        }
    )
})
serializer = factory.serializer(List[Todo])

# test
todos = [Todo(
    id=i,
    title="title %s" % i,
    desc="5some long description %s %s %s" % (i, i * 10, i)
) for i in range(10)]


def do1():
    return serializer(todos)


# print(json.dumps(do1()[0], indent=2))
print("my    ", timeit("do()", globals={"do": do1}, number=100000))
