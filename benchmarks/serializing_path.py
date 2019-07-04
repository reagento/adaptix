from dataclasses import dataclass
from timeit import timeit
from typing import List

from dataclass_factory import Factory, Schema as DSchema


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
    SimpleTodo: DSchema(
        name_mapping={
            "desc": ("description", "qwerty", 0),
        }
    )
})
simple_serializer = factory.serializer(List[SimpleTodo])
complex_serializer = factory.serializer(List[ComplexTodo])

# test
simple_todos = [SimpleTodo(
    id=i,
    title="title %s" % i,
    desc="5some long description %s %s %s" % (i, i * 10, i)
) for i in range(10)]

complex_todos = [ComplexTodo(
    id=i,
    title="title %s" % i,
    description=Qwerty(["5some long description %s %s %s" % (i, i * 10, i)])
) for i in range(10)]


def do_simple():
    return simple_serializer(simple_todos)


def do_complex():
    return complex_serializer(complex_todos)


assert do_complex() == do_simple()
# print(json.dumps(do1()[0], indent=2))
print("simple ", timeit("do()", globals={"do": do_simple}, number=100000))  # 1.9579019670491107
print("complex", timeit("do()", globals={"do": do_complex}, number=100000))  # 1.8429706260212697
