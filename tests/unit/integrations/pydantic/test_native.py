from pydantic import BaseModel, ValidationError
from tests_helpers import raises_exc, with_cause

from adaptix import Retort
from adaptix._internal.integrations.pydantic.native import native_pydantic
from adaptix._internal.morphing.load_error import LoadError


def create_stub_validation_error():
    error = ValidationError.from_exception_data(title="", line_errors=[])
    error.args = []
    return error


def test_validation_without_params():
    class MyModel(BaseModel):
        a: int
        b: str

    retort = Retort(
        recipe=[native_pydantic(MyModel)],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "abc", "b": "value"}),
    )


def test_with_params():
    class MyModel(BaseModel):
        a: int
        b: str

    retort = Retort(
        recipe=[native_pydantic(MyModel, strict=True)],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "1", "b": "value"}),
    )

    dumper_ = retort.get_dumper(MyModel)
    assert dumper_(MyModel(a=1, b="value")) == {"a": 1, "b": "value"}


def test_serialization_with_params():
    class MyModel(BaseModel):
        a: int
        b: str

    retort = Retort(
        recipe=[native_pydantic(MyModel, strict=True)],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "1", "b": "value"}),
    )

    dumper_ = retort.get_dumper(MyModel)
    assert dumper_(MyModel(a=1, b="value")) == {"a": 1, "b": "value"}
