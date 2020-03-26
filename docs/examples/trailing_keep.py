from dataclasses import dataclass

import dataclass_factory
from dataclass_factory import Schema


@dataclass
class Period:
    from_: int
    to_: int


data = {
    "from_": 1,
    "to_": 100,
}

factory = dataclass_factory.Factory(default_schema=Schema(trim_trailing_underscore=False))
period = factory.load(data, Period)
factory.dump(period)
