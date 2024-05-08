from adaptix._internal.conversion.facade.provider import coercer
from adaptix.conversion import impl_converter, link_function


def test_only_model(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: int

    def my_function(model):
        return model_spec.get_field(model, "field2")

    @impl_converter(recipe=[link_function(my_function, "field3")])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=10)) == DestModel(field1=1, field3=10)


def test_converter_parameter(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: int

    def my_function(model, foo: int):
        return model_spec.get_field(model, "field2") + foo

    @impl_converter(recipe=[link_function(my_function, "field3")])
    def convert(a: SourceModel, foo: int) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=10), foo=20) == DestModel(field1=1, field3=30)


def test_model_field(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: str

    def my_function(model, *, field2: str):
        return field2

    @impl_converter(
        recipe=[
            link_function(my_function, "field3"),
            coercer(int, str, func=str),
        ],
    )
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=10)) == DestModel(field1=1, field3="10")
