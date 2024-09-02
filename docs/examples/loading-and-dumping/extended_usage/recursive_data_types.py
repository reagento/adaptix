# ruff: noqa: UP006, UP035
from dataclasses import dataclass
from typing import List

from adaptix import Retort


@dataclass
class ItemCategory:
    id: int
    name: str
    sub_categories: List["ItemCategory"]


retort = Retort()

data = {
    "id": 1,
    "name": "literature",
    "sub_categories": [
        {
            "id": 2,
            "name": "novel",
            "sub_categories": [],
        },
    ],
}
item_category = retort.load(data, ItemCategory)
assert item_category == ItemCategory(
    id=1,
    name="literature",
    sub_categories=[
        ItemCategory(
            id=2,
            name="novel",
            sub_categories=[],
        ),
    ],
)
assert retort.dump(item_category) == data
