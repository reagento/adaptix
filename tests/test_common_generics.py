from unittest import TestCase

from dataclasses import dataclass

from dataclass_factory import Factory


@dataclass
class A:
    value: int


class Test1(TestCase):
    def test_list(self):
        factory = Factory()
        self.assertEqual(factory.dump([A(1)]), [{"value": 1}])

    def test_dict(self):
        factory = Factory()
        self.assertEqual(factory.dump({"a": A(1)}), {"a": {"value": 1}})
