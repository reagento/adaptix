from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Empty:
    pass


def test_simple(accum):
    retort = Retort(recipe=[accum])

    loader = retort.get_loader(Empty)
    assert loader({"some_field": 1}) == Empty()

    dumper = retort.get_dumper(Empty)
    assert dumper(Empty()) == {}
