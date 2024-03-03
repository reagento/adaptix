from dataclasses import dataclass

from adaptix import Retort


def test_type_alias():
    retort = Retort()

    type MyAlias = int

    @dataclass
    class Foo:
        bar: MyAlias

    assert retort.load({"bar": 10}, Foo) == Foo(bar=10)
    assert retort.dump(Foo(bar=10)) == {"bar": 10}


def test_type_alias_type_vars():
    retort = Retort()

    type MyAlias[T] = list[T]

    @dataclass
    class Foo:
        bar: MyAlias[int]

    assert retort.load({"bar": [10]}, Foo) == Foo(bar=[10])
    assert retort.dump(Foo(bar=[10])) == {"bar": [10]}


def test_type_alias_type_vars_generics():
    retort = Retort()

    type MyAlias[T] = list[T]

    @dataclass
    class Foo[T]:
        bar: MyAlias[T]

    assert retort.load({"bar": [10]}, Foo) == Foo(bar=[10])
    assert retort.dump(Foo(bar=[10]), Foo[int]) == {"bar": [10]}
