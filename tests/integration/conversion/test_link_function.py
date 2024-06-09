from tests_helpers import raises_exc, with_cause, with_notes

from adaptix import AggregateCannotProvide, CannotProvide, ProviderNotFoundError
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

    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce converter for"
                    f" <Signature (src: {SourceModel.__module__}.{SourceModel.__qualname__}, /)"
                    f" -> {DestModel.__module__}.{DestModel.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Linkings for some fields are not found",
                            [
                                with_notes(
                                    AggregateCannotProvide(
                                        "Cannot create linking for function."
                                        " Linkings for some parameters are not found",
                                        [
                                            with_notes(
                                                CannotProvide(
                                                    f"Cannot match `{my_function.__qualname__}(p1: str)`"
                                                    f" with converter parameter",
                                                    is_terminal=True,
                                                    is_demonstrative=True,
                                                ),
                                            ),
                                            with_notes(
                                                CannotProvide(
                                                    f"Cannot match `{my_function.__qualname__}(f1: str)`"
                                                    f" with model field",
                                                    is_terminal=True,
                                                    is_demonstrative=True,
                                                ),
                                            ),
                                        ],
                                        is_terminal=True,
                                        is_demonstrative=True,
                                    ),
                                    f"Linking: `{SourceModel.__qualname__} => {DestModel.__qualname__}.field3: str`",
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{SourceModel.__qualname__} => {DestModel.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(SourceModel, DestModel, recipe=[link_function(my_function, "field3")]),
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

    raises_exc(
        with_cause(
            with_notes(
                ProviderNotFoundError(
                    f"Cannot produce converter for"
                    f" <Signature (src: {SourceModel.__module__}.{SourceModel.__qualname__}, p1: int)"
                    f" -> {DestModel.__module__}.{DestModel.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Coercers for some linkings are not found",
                            [
                                with_notes(
                                    AggregateCannotProvide(
                                        "Cannot create coercer for model and function."
                                        " Coercers for some linkings are not found",
                                        [
                                            with_notes(
                                                CannotProvide(
                                                    "Cannot find coercer",
                                                    is_terminal=False,
                                                    is_demonstrative=True,
                                                ),
                                                f"Linking: `int => {my_function.__qualname__}(p1: str)`",
                                            ),
                                            with_notes(
                                                CannotProvide(
                                                    "Cannot find coercer",
                                                    is_terminal=False,
                                                    is_demonstrative=True,
                                                ),
                                                f"Linking: `{SourceModel.__qualname__}.field1: int"
                                                f" => {my_function.__qualname__}(field1: str)`",
                                            ),
                                        ],
                                        is_terminal=True,
                                        is_demonstrative=True,
                                    ),
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{SourceModel.__qualname__} => {DestModel.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        make_converter,
    )
