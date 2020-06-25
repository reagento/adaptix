import json
from enum import Enum
from typing import Dict, Union

from dataclasses import dataclass, field

from dataclass_factory import Factory, Schema


class A(Enum):
    X = "x"
    Y = 1


@dataclass
class Data:
    a: A
    dict_: Dict[str, Union[int, float]]
    dictw_: Dict[str, Union[int, float]] = field(default_factory=dict)
    optional_num: int = 0


factory = Factory(schemas={A: Schema(description="My super `A` class")})
print(json.dumps(factory.json_schema(Data), indent=2))
print(json.dumps(factory.json_schema_definitions(), indent=2))
