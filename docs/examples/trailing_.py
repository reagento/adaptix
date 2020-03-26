from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Period:
    from_: int
    to_: int


data = {
    "from": 1,
    "to": 100,
}

factory = dataclass_factory.Factory()
period = factory.load(data, Period)
