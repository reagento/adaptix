from typing import Optional, Dict

from dataclasses import dataclass

from dataclass_factory import Factory, Schema


@dataclass
class Sub:
    b: str


@dataclass
class Data:
    a: str
    unknown: Optional[Dict] = None
    sub: Optional[Sub] = None


serialized = {
    "a": "A1",
    "b": "B2",
    "c": "C3",
}

factory = Factory(default_schema=Schema(unknown=["unknown", "sub"]))
data = factory.load(serialized, Data)
assert data == Data(a="A1", unknown={"b": "B2", "c": "C3"}, sub=Sub("B2"))
