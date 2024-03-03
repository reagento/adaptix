from dataclasses import dataclass

from adaptix import Retort, loader


@dataclass
class Foo:
    value: int


def add_one(data):
    return data + 1


def add_two(data):
    return data + 2


retort = Retort(
    recipe=[
        loader(int, add_one),
        loader(int, add_two),
    ],
)

assert retort.load({"value": 10}, Foo) == Foo(11)
