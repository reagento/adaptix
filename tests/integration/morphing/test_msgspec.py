from typing import ClassVar, Generic, TypeVar

from msgspec import Struct, field

from adaptix import Retort


def test_basic(accum):
    class MyModel(Struct):
        f1: int
        f2: str

    retort = Retort(recipe=[accum])
    assert retort.load({"f1": 0, "f2": "a"}, MyModel) == MyModel(f1=0, f2="a")
    assert retort.dump(MyModel(f1=0, f2="a")) == {"f1": 0, "f2": "a"}

T = TypeVar("T")

def test_all_field_kinds(accum):
    class MyModel(Struct, Generic[T]):
        a: int
        b: T
        c: str = field(default="c", name="_c")
        d: ClassVar[float] = 2.11


    retort = Retort(recipe=[accum])
    assert retort.load({"a": 0, "b": 3}, MyModel[int]) == MyModel(a=0, b=3)
    assert retort.dump(MyModel(a=0, b=True), MyModel[bool]) == {"a": 0, "b": True, "c": "c"}
