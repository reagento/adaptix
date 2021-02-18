from dataclasses import dataclass
import sys
import unittest
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class Model:
    name: str


factory = Factory()


@unittest.skipUnless(sys.version_info[:2] >= (3, 9), "requires Python 3.9+")
class TestTypeHintingGenericsInStandartCollections(TestCase):
    def test_dict(self):
        data = {
            "model": {
                "name": "name1",
            },
            "model2": {
                "name": "name2",
            },
        }
        expected = {"model": Model("name1"), "model2": Model("name2")}
        self.assertEqual(expected, factory.load(data, dict[str, Model]))

    def test_list(self):
        data = [
            {
                "name": "name1",
            },
            {
                "name": "name2",
            },
        ]
        expected = [Model("name1"), Model("name2")]
        self.assertEqual(expected, factory.load(data, list[Model]))
