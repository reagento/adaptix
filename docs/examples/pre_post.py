import json
from typing import List

from dataclasses import dataclass

from dataclass_factory import Schema, Factory


@dataclass
class Data:
    items: List[str]
    name: str


def post_serialize(data):
    data["items"] = json.dumps(data["items"])
    return data


def pre_parse(data):
    data["items"] = json.loads(data["items"])
    return data


def post_parse(data: Data) -> Data:
    if not data.name:
        raise ValueError("Name must not be empty")
    return data


data_schema = Schema[Data](
    post_serialize=post_serialize,
    pre_parse=pre_parse,
    post_parse=post_parse,
)
factory = Factory(schemas={Data: data_schema})

data = Data(['a', 'b'], 'My Name')
serialized = {'items': '["a", "b"]', 'name': 'My Name'}
assert factory.dump(data) == serialized
assert factory.load(serialized, Data) == data

try:
    factory.load({'items': '[]', 'name': ''}, Data)
except ValueError as e:
    print("Error detected:", e)  # Error detected: Name must not be empty
