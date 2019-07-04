from dataclasses import dataclass
from timeit import timeit
from typing import List

from dataclass_factory import Factory, Schema


@dataclass
class SimpleTodo:
    id: int
    title: str
    desc: str


@dataclass
class Qwerty:
    qwerty: List[str]


@dataclass
class ComplexTodo:
    id: int
    title: str
    description: Qwerty


# my
factory = Factory(schemas={
    SimpleTodo: Schema(
        name_mapping={
            "desc": ("description", "qwerty", 0),
        }
    )
}, debug_path=True)
simple_parser = factory.parser(List[SimpleTodo])
complex_parser = factory.parser(List[ComplexTodo])

# test
todos = [{
    "description": {
        "qwerty": [
            "5some long description %s %s %s" % (i, i * 10, i)
        ],
    },
    "id": i,
    "title": "title %s" % i,
} for i in range(10)]


def do_simple():
    return simple_parser(todos)


def do_complex():
    return complex_parser(todos)


print("simple ", timeit("do()", globals={"do": do_simple}, number=100000))  # 2.015210837998893
print("complex", timeit("do()", globals={"do": do_complex}, number=100000))  # 3.569017971982248
