from msgspec import Struct, ValidationError
from tests_helpers import raises_exc, with_cause

from adaptix import Retort
from adaptix._internal.integrations.msgspec.native import native_msgspec
from adaptix._internal.morphing.load_error import LoadError


def create_stub_validation_error():
    error = ValidationError()
    error.args = ["Expected `int`, got `str` - at `$.a`"]
    return error


def test_validation_without_params():
    class MyModel(Struct):
        a: int
        b: str

    retort = Retort(
        recipe=[native_msgspec(MyModel)],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "abc", "b": "value"}),
    )


def test_with_conversion_params():
    class MyModel(Struct):
        a: int
        b: str

    retort = Retort(
        recipe=[native_msgspec(MyModel, convert={"strict": True})],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "1", "b": "value"}),
    )

    dumper_ = retort.get_dumper(MyModel)
    assert dumper_(MyModel(a=1, b="value")) == {"a": 1, "b": "value"}


def test_to_builtins_with_params():
    class MyModel(Struct):
        a: int
        b: str

    retort = Retort(
        recipe=[native_msgspec(MyModel, to_builtins={"str_keys": False})],
    )

    loader_ = retort.get_loader(MyModel)
    assert loader_({"a": 1, "b": "value"}) == MyModel(a=1, b="value")
    raises_exc(
        with_cause(LoadError(), create_stub_validation_error()),
        lambda: loader_({"a": "1", "b": "value"}),
    )

    dumper_ = retort.get_dumper(MyModel)
    assert dumper_(MyModel(a=1, b="value")) == {"a": 1, "b": "value"}
