from dataclasses import dataclass
from typing import TypeVar, Generic

from dataclass_factory import Factory, Schema

T = TypeVar("T")


@dataclass
class FakeFoo(Generic[T]):
    value: T


factory = Factory(schemas={
    FakeFoo[str]: Schema(name_mapping={"value": "s"}),
    FakeFoo: Schema(name_mapping={"value": "i"}),
})
data = {"i": 42, "s": "Hello"}
assert factory.load(data, FakeFoo[str]) == FakeFoo("Hello")  # found schema for concrete type
assert factory.load(data, FakeFoo[int]) == FakeFoo(42)  # schema taken from generic version
assert factory.dump(FakeFoo("hello"), FakeFoo[str]) == {"s": "hello"}  # concrete type is set explicitly
assert factory.dump(FakeFoo("hello")) == {"i": "hello"}  # generic type is detected automatically
