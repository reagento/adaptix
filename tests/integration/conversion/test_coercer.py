from typing import Any

import pytest

from adaptix.conversion import coercer, get_converter, impl_converter

from .local_helpers import FactoryWay


@pytest.mark.parametrize(
    "func",
    [
        pytest.param(int, id="int"),
        pytest.param(lambda x: int(x), id="lambda"),
    ],
)
def test_simple(src_model_spec, dst_model_spec, factory_way, func):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: str
        field2: str

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: int
        field2: int

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[coercer(str, int, func=func)])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[coercer(str, int, func=func)])

    assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1=1, field2=2)


def test_model_priority(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModelNested(*src_model_spec.bases):
        field1: Any

    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any
        nested: SourceModelNested

    @dst_model_spec.decorator
    class DestModelNested(*dst_model_spec.bases):
        field1: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any
        nested: DestModelNested

    def my_coercer(a: SourceModelNested) -> DestModelNested:
        return DestModelNested(field1=src_model_spec.get_field(a, "field1") + 10)

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[coercer(SourceModelNested, DestModelNested, func=my_coercer)])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(
            SourceModel,
            DestModel,
            recipe=[coercer(SourceModelNested, DestModelNested, func=my_coercer)],
        )

    assert convert(
        SourceModel(
            field1=1,
            field2=2,
            nested=SourceModelNested(field1=3),
        ),
    ) == DestModel(
        field1=1,
        field2=2,
        nested=DestModelNested(field1=13),
    )


def test_any_dest(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: str
        field2: str

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1="1", field2="2")


def test_subclass_builtin(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: bool
        field2: bool

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: int
        field2: int

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(SourceModel(field1=False, field2=True)) == DestModel(field1=False, field2=True)
