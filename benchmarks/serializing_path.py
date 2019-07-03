from dataclasses import dataclass, asdict
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
        name_mapping={"desc": ("description", "qwerty", 0)}
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


print("my    ", timeit("do()", globals={"do": do1}, number=100000))
