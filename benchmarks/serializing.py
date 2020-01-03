from timeit import timeit
from typing import List

from dataclasses import dataclass, asdict
from marshmallow import Schema, fields
from mashumaro import DataClassDictMixin

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


# mashumaro

@dataclass
class MashumaroTodo(DataClassDictMixin):
    id: int
    title: str
    description: str


mashumaro_todos = [MashumaroTodo(
    id=i,
    title="title %s" % i,
    description="5some long description %s %s %s" % (i, i * 10, i)
) for i in range(10)]


def do1():
    return serializer(todos)


def do2():
    return todo_schema.dump(todos)


def do3():
    return [asdict(t) for t in todos]


def do4():
    return [t.to_dict() for t in mashumaro_todos]


assert do1() == do2()

print("my    ", timeit("do()", globals={"do": do1}, number=100000))  # 0.7900586039977497
print("mashum", timeit("do()", globals={"do": do4}, number=100000))  # 0.5299071890003688
print("marsh ", timeit("do()", globals={"do": do2}, number=100000))  # 5.793430982997961
print("asdict", timeit("do()", globals={"do": do3}, number=100000))  # 6.109174378001626
