from typing import Union

from dataclasses import dataclass

from dataclass_factory import Factory, Schema
from dataclass_factory.schema_helpers import type_checker


@dataclass
class Item:
    name: str
    type: str = "item"


@dataclass
class Group:
    name: str
    type: str = "group"


Something = Union[Item, Group]  # Available types

factory = Factory(schemas={
    Item: Schema(pre_parse=type_checker("item", field="type")),
    Group: Schema(pre_parse=type_checker("group")),  # `type` is default name for checked field
})

assert factory.load({"name": "some name", "type": "group"}, Something) == Group("some name")
