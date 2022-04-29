from timeit import timeit
from typing import List

from dataclasses import dataclass
from marshmallow import Schema, fields, post_load
from mashumaro import DataClassDictMixin
from pydantic import BaseModel, Field

from dataclass_factory import Factory, Schema as DSchema
from dataclass_factory_30.factory import Factory as NewFactory


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

# my debug
factory_debug = Factory(schemas={
    Todo: DSchema(
        name_mapping={"desc": "description"}
    )
}, debug_path=True)
parser_debug = factory_debug.parser(List[Todo])


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


def do1_debug():
    return parser_debug(todos)


def do2():
    return todo_schema.load(todos)


def do3():
    return TodoList.parse_obj(todos)


def do4():
    return [MashumaroTodo.from_dict(x) for x in todos]


assert do1() == do2()


@dataclass
class TodoDesc:
    id: int
    title: str
    description: str


new_factory = NewFactory(strict_coercion=False, debug_path=True)
new_parser = new_factory.parser(List[TodoDesc])


def do5():
    return new_parser(todos)


print("my-new   ", timeit("do()", globals={"do": do5}, number=100000))  #
#print("my       ", timeit("do()", globals={"do": do1}, number=100000))  # 1.5959172130096704
#print("my debug ", timeit("do()", globals={"do": do1_debug}, number=100000))  # 2.087571810989175
print("mashumaro", timeit("do()", globals={"do": do4}, number=100000))  # 1.459100882988423
#print("marsh    ", timeit("do()", globals={"do": do2}, number=100000))  # 21.77947078004945
#print("mpydantic", timeit("do()", globals={"do": do3}, number=100000))  # 7.471431287995074
