from dataclasses import dataclass
from typing import Protocol

from dataclass_factory import Factory


class P(Protocol):
    pass


@dataclass
class D(P):
    field: int


def test_protocol_parsed():
    factory = Factory()
    data = {"field": 1}
    parsed = D(1)

    assert factory.load(data, D) == parsed
    assert factory.dump(parsed) == data
