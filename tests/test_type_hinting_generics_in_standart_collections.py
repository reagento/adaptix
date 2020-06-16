from dataclasses import dataclass
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class Model:
    name: str
    list: list[int]
    dict: dict[int, int]


factory = Factory()


class TestTypeHintingGenericsInStandartCollections(TestCase):
    def test_dict(self):
        data = {
            "model": {
                "name": "name",
                "list": [1, 2, 3, 4, 5],
                "dict": {
                    1: 1,
                    2: 2,
                    3: 3,
                    4: 4,
                },
            },
            "model2": {
                "name": "name",
                "list": [1, 2, 3, 4, 5],
                "dict": {
                    1: 1,
                    2: 2,
                    3: 3,
                    4: 4,
                },
            },
        }
        self.assertTrue(factory.load(data, dict[str, Model]))

    def test_list(self):
        data = [
            {
                "name": "name",
                "list": [1, 2, 3, 4, 5],
                "dict": {
                    1: 1,
                    2: 2,
                    3: 3,
                    4: 4,
                }
            },
            {
                "name": "name",
                "list": [1, 2, 3, 4, 5],
                "dict": {
                    1: 1,
                    2: 2,
                    3: 3,
                    4: 4,
                },
            },
        ]
        self.assertTrue(factory.load(data, list[Model]))
