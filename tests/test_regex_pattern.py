from dataclasses import dataclass
from unittest import TestCase
from re import compile, Pattern

from dataclass_factory import Factory


@dataclass
class RegexPattern:
    pattern: Pattern


class TestFactory(TestCase):
    def test_pattern(self):
        factory = Factory()
        data_object = RegexPattern(pattern=compile(r"testcase"))
        data = {"pattern": "testcase"}

        self.assertEqual(factory.load(data, RegexPattern), data_object)
