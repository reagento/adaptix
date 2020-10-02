from dataclasses import dataclass, field
from typing import List
from unittest import TestCase

from dataclass_factory import Factory, Schema


@dataclass
class Data:
    x: int = 1
    y: List = field(default_factory=list)
    z: str = field(default="test")


schema = Schema[Data](omit_default=True)


class TestDefault(TestCase):
    def test_optional(self):
        factory = Factory(default_schema=schema)
        self.assertEqual(factory.dump(Data()), {})
        self.assertEqual(factory.dump(Data(1, [], "test")), {})
        self.assertEqual(factory.dump(Data(2, [], "test")), {"x": 2})
