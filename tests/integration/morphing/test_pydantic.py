from pydantic import BaseModel, computed_field

from adaptix import Retort


def test_basic(accum):
    class MyModel(BaseModel):
        f1: int
        f2: str

    retort = Retort(recipe=[accum])
    assert retort.load({"f1": 0, "f2": "a"}, MyModel) == MyModel(f1=0, f2="a")
    assert retort.dump(MyModel(f1=0, f2="a")) == {"f1": 0, "f2": "a"}


def test_all_field_kinds(accum):
    class MyModel(BaseModel):
        a: int

        @computed_field
        @property
        def b(self) -> str:
            return "b_value"

        _c: int

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._c = 2

    retort = Retort(recipe=[accum])
    assert retort.load({"a": 0}, MyModel) == MyModel(a=0)
    assert retort.dump(MyModel(a=0)) == {"a": 0, "b": "b_value"}
