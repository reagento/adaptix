from dataclasses import dataclass
from unittest import TestCase

from typing import List

from dataclass_factory import Factory, Schema


@dataclass
class Data:
    items: List[str]


def post_serialize(data):
    data["items"] = ",".join(data["items"])
    return data


def pre_parse(data):
    data["items"] = data["items"].split(",")
    return data


def pre_serialize(data: Data) -> Data:
    return Data([
        x + '!' for x in data.items
    ])


def post_parse(data: Data) -> Data:
    return Data([
        x[:-1] for x in data.items
    ])


schema_outer = Schema[Data](
    post_serialize=post_serialize,
    pre_parse=pre_parse,
)

schema_inner = Schema[Data](
    pre_serialize=pre_serialize,
    post_parse=post_parse,
)


class Test1(TestCase):
    def test_post_serialize(self):
        factory = Factory(schemas={Data: schema_outer})
        data = Data(["a", "b"])
        expected = {"items": "a,b"}
        self.assertEqual(factory.dump(data), expected)

    def test_pre_parser(self):
        factory = Factory(schemas={Data: schema_outer})
        expected = Data(["a", "b"])
        data = {"items": "a,b"}
        self.assertEqual(factory.load(data, Data), expected)

    def test_pre_serialize(self):
        factory = Factory(schemas={Data: schema_inner})
        data = Data(["a", "b"])
        expected = {"items": ["a!", "b!"]}
        self.assertEqual(factory.dump(data), expected)

    def test_post_parser(self):
        factory = Factory(schemas={Data: schema_inner})
        expected = Data(["a", "b"])
        data = {"items": ["a!", "b!"]}
        self.assertEqual(factory.load(data, Data), expected)
