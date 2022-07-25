from timeit import timeit
from typing import List

from dataclasses import dataclass
from marshmallow import Schema, fields, post_load
from mashumaro import DataClassDictMixin
from pydantic import BaseModel, Field

from dataclass_factory import Factory, Schema as DSchema
from dataclass_factory_30.facade.factory import Factory as NewFactory
from dataclass_factory_30.facade.provider import name_mapping


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


def df_old():
    return parser(todos)


def df_old_debug():
    return parser_debug(todos)


def do2():
    return todo_schema.load(todos)


def do3():
    return TodoList.parse_obj(todos)


def mashum():
    return [MashumaroTodo.from_dict(x) for x in todos]


assert df_old() == do2()


new_factory = NewFactory(
    strict_coercion=False,
    debug_path=False,
    recipe=[name_mapping(Todo, map={"desc": "description"})]
)
new_parser = new_factory.parser(List[Todo])


new_factory_debug = NewFactory(
    strict_coercion=False,
    debug_path=True,
    recipe=[name_mapping(Todo, map={"desc": "description"})]
)
new_parser_debug = new_factory_debug.parser(List[Todo])


def df_new():
    return new_parser(todos)


def df_new_debug():
    return new_parser_debug(todos)


if __name__ == '__main__':
    print("my-new      ", timeit("do()", globals={"do": df_new}, number=100000))  # 0.8271589210489765
    print("my-new debug", timeit("do()", globals={"do": df_new_debug}, number=100000))  # 0.9333962750388309
    print("my          ", timeit("do()", globals={"do": df_old}, number=100000))  # 1.1393319150665775
    print("my debug    ", timeit("do()", globals={"do": df_old_debug}, number=100000))  # 1.4068040259880945
    print("mashumaro   ", timeit("do()", globals={"do": mashum}, number=100000))  # 0.9388460679911077
    print("marsh       ", timeit("do()", globals={"do": do2}, number=100000))  # 15.152756247087382
    print("mpydantic   ", timeit("do()", globals={"do": do3}, number=100000))  # 7.089421317912638
