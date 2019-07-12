from typing import List
from unittest import TestCase

from dataclasses import dataclass

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


schema = Schema[Data](
    post_serialize=post_serialize,
    pre_parse=pre_parse,
)


class Test1(TestCase):
    def test_post_serialize(self):
        factory = Factory(schemas={Data: schema})
        data = Data(["a", "b"])
        expected = {"items": "a,b"}
        self.assertEqual(factory.dump(data), expected)

    def test_pre_parser(self):
        factory = Factory(schemas={Data: schema})
        expected = Data(["a", "b"])
        data = {"items": "a,b"}
        self.assertEqual(factory.load(data, Data), expected)
