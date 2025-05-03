from tests_helpers.misc import raises_exc_text

from adaptix._internal.conversion.facade.func import get_converter
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


def test_only_keyword_only_parameters(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: int

    def my_function(*, field1: int, field2: int):
        return field1 + field2

    @impl_converter(
        recipe=[
            link_function(my_function, "field3"),
        ],
    )
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=10)) == DestModel(field1=1, field3=11)


def test_linking_error(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: str

    def my_function(model, p1: str, *, f1: str):
        return model

    raises_exc_text(
        lambda: get_converter(SourceModel, DestModel, recipe=[link_function(my_function, "field3")]),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.SourceModel, /) -> __main__.DestModel>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Linkings for some fields are not found
             │ Linking: ‹src: SourceModel› ──▷ DestModel
             ╰──▷ Cannot create linking for function ‹my_function›. Linkings for some parameters are not found
                │ Linking: ‹src: SourceModel› ──▷ ‹DestModel.field3: str›
                ├──▷ Cannot match function parameter ‹p1› with any converter parameter
                ╰──▷ Cannot match function parameter ‹f1› with any model field
        """,
        {
            "SourceModel": SourceModel.__qualname__,
            "DestModel": DestModel.__qualname__,
            "my_function": my_function.__qualname__,
            "__main__": __name__,
        },
    )


def test_cannot_find_coercer_error(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field3: str

    def my_function(model, p1: str, *, field1: str):
        return model

    def make_converter():
        @impl_converter(recipe=[link_function(my_function, "field3")])
        def convert(src: SourceModel, p1: int) -> DestModel:
            pass

    raises_exc_text(
        make_converter,
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.SourceModel, p1: int) -> __main__.DestModel>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Coercers for some linkings are not found
             │ Linking: ‹src: SourceModel› ──▷ DestModel
             ╰──▷ Cannot create coercer for model and function ‹my_function›. Coercers for some linkings are not found
                │ Linking: ‹src: SourceModel› ──▷ ‹DestModel.field3: str›
                ├──▷ Cannot find coercer
                │    Linking: ‹p1: int› ──▷ parameter ‹p1: str›
                ╰──▷ Cannot find coercer
                     Linking: ‹SourceModel.field1: int› ──▷ parameter ‹field1: str›
        """,
        {
            "SourceModel": SourceModel.__qualname__,
            "DestModel": DestModel.__qualname__,
            "my_function": my_function.__qualname__,
            "__main__": __name__,
        },
    )
