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


# marshmallow
class TodoSchema(Schema):
    id = fields.Integer()
    title = fields.Str()
    description = fields.Str(attribute="desc")

    @post_load
    def post(self, data):
        return Todo(**data)


todo_schema = TodoSchema(many=True)

# my
factory = Factory(schemas={
    Todo: DSchema(
        name_mapping={"desc": "description"}
    )
})
parser = factory.parser(List[Todo])

# test
todos = [{
    "id": i,
    "title": "title %s" % i,
    "description": "5some long description %s %s %s" % (i, i * 10, i)
} for i in range(10)]


def do1():
    return parser(todos)


def do2():
    return todo_schema.load(todos)[0]


assert do1() == do2()

print("my   ", timeit("do()", globals={"do": do1}, number=100000))  # 1.1471970899983717
print("marsh", timeit("do()", globals={"do": do2}, number=100000))  # 9.297098876999371
