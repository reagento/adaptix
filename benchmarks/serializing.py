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


# marshmallow
class TodoSchema(Schema):
    id = fields.Integer()
    title = fields.Str()
    description = fields.Str(attribute="desc")


todo_schema = TodoSchema(many=True)

# my
factory = Factory(schemas={
    Todo: DSchema(
        name_mapping={"desc": "description"}
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


def do2():
    return todo_schema.dump(todos)


def do3():
    return [asdict(t) for t in todos]


assert do1() == do2()

print("my    ", timeit("do()", globals={"do": do1}, number=100000))  # 2.026152505999562
print("marsh ", timeit("do()", globals={"do": do2}, number=100000))  # 6.001530854000521
print("asdict", timeit("do()", globals={"do": do3}, number=100000))  # 6.57121034499869
