from timeit import timeit
from typing import List

from dataclasses import dataclass
from marshmallow import Schema, fields, post_load
from mashumaro import DataClassDictMixin
from pydantic import BaseModel, Field

from dataclass_factory import Factory, Schema as DSchema


@dataclass
class Todo:
    id: int
    title: str
    desc: str


# pydantic
class PydanticTodo(BaseModel):
    id: int
    title: str
    desc: str = Field(None, alias='description')


class TodoList(BaseModel):
    __root__: List[PydanticTodo]


# marshmallow
class TodoSchema(Schema):
    id = fields.Integer()
    title = fields.Str()
    description = fields.Str(attribute="desc")

    @post_load
    def post(self, data, **kwargs):
        return Todo(**data)


todo_schema = TodoSchema(many=True)

# my
factory = Factory(schemas={
    Todo: DSchema(
        name_mapping={"desc": "description"}
    )
})
parser = factory.parser(List[Todo])


# pydantic
class PydTodo(BaseModel):
    id: int
    title: str
    description: str


# mashumaro

@dataclass
class MashumaroTodo(DataClassDictMixin):
    id: int
    title: str
    description: str


# test
todos = [{
    "id": i,
    "title": "title %s" % i,
    "description": "5some long description %s %s %s" % (i, i * 10, i)
} for i in range(10)]


def do1():
    return parser(todos)


def do2():
    return todo_schema.load(todos)


def do3():
    return TodoList.parse_obj(todos)


def do4():
    return [MashumaroTodo.from_dict(x) for x in todos]


assert do1() == do2()

print("my       ", timeit("do()", globals={"do": do1}, number=100000))  # 1.6099195899987535
print("mashumaro", timeit("do()", globals={"do": do4}, number=100000))  # 1.3904066249997413
print("marsh    ", timeit("do()", globals={"do": do2}, number=100000))  # 18.798911712001427
print("mpydantic", timeit("do()", globals={"do": do3}, number=100000))  # 6.867118302001472
