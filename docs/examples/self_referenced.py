from typing import Any, Optional

from dataclasses import dataclass

import dataclass_factory


@dataclass
class LinkedItem:
    value: Any
    next: Optional["LinkedItem"] = None


data = {
    "value": 1,
    "next": {
        "value": 2
    }
}

factory = dataclass_factory.Factory()
items = factory.load(data, LinkedItem)
# items = LinkedItem(1, LinkedItem(2))
