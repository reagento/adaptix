from dataclasses import dataclass

from typing_extensions import Protocol
# typing_extensions just propagates typing.Protocol on python 3.8+

from dataclass_factory import Factory


class MyProto(Protocol):
    pass


@dataclass
class Data(MyProto):
    field: int


def test_protocol_parsed():
    factory = Factory()
    data = {"field": 1}
    parsed = Data(1)

    assert factory.load(data, Data) == parsed
    assert factory.dump(parsed) == data
