from dataclasses import dataclass, field
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class Data:
    a: str = field(init=False)
    b: str


class TestIgnoreFieldsWithInitFalse(TestCase):
    def test_ignore_fields_with_init_false(self):
        serial = {"a": "A", "b": "B"}
        factory = Factory()
        self.assertTrue(factory.load(serial, Data))
