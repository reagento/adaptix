from dataclasses import dataclass

from adaptix import Retort, name_mapping


def test_simple(accum):
    @dataclass
    class Example:
        c: int
        a: int
        b: int

    retort = Retort(recipe=[accum])

    dumper = retort.get_dumper(Example)
    assert list(dumper(Example(c=1, a=2, b=3)).items()) == [("c", 1), ("a", 2), ("b", 3)]


def test_name_flatenning(accum):
    @dataclass
    class Example:
        c: int
        a: int
        e: int
        b: int

    retort = Retort(
        recipe=[
            accum,
            name_mapping(Example, map={"e": ("q", "e")}),
        ],
    )

    dumper = retort.get_dumper(Example)
    assert list(dumper(Example(c=1, a=2, e=3, b=4)).items()) == [("c", 1), ("a", 2), ("b", 4), ("q", {"e": 3})]
