from dataclasses import dataclass
from typing import TypeVar

# typing_extensions just propagates typing.Protocol on python 3.8+
from typing_extensions import Protocol

from dataclass_factory import Factory


class MyProto(Protocol):
    pass


@dataclass
class Data(MyProto):
    field: int


T = TypeVar("T")


class MyGenericProto(Protocol[T]):
    pass


@dataclass
class IntGenericData(MyGenericProto[int]):
    field: int


@dataclass
class AnyGenericData(MyGenericProto):
    field: int


def test_protocol_parsed():
    factory = Factory()
    data = {"field": 1}
    parsed = Data(1)

    assert factory.load(data, Data) == parsed
    assert factory.dump(parsed) == data


def test_generic_parsed():
    factory = Factory()
    data = {"field": 1}
    parsed = IntGenericData(1)

    assert factory.load(data, IntGenericData) == parsed
    assert factory.dump(parsed) == data


def test_any_generic_parsed():
    factory = Factory()
    data = {"field": 1}
    parsed = AnyGenericData(1)

    assert factory.load(data, AnyGenericData) == parsed
    assert factory.dump(parsed) == data
