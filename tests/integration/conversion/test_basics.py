from typing import Any

import pytest

from adaptix.conversion import get_converter, impl_converter

from .local_helpers import FactoryWay


@pytest.mark.parametrize('way', FactoryWay.params())
def test_copy(model_spec, way):
    @model_spec.decorator
    class ExampleAny(*model_spec.bases):
        field1: Any
        field2: Any

    if way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def copy(a: ExampleAny) -> ExampleAny:
            ...
    else:
        copy = get_converter(ExampleAny, ExampleAny)

    obj1 = ExampleAny(field1=1, field2=2)
    assert copy(obj1) == obj1
    assert copy(obj1) is not obj1


@pytest.mark.parametrize('way', FactoryWay.params())
def test_same_shape(src_model_spec, dst_model_spec, way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    if way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(SourceModel(field1=1, field2=2)) == DestModel(field1=1, field2=2)


def test_replace(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    @impl_converter
    def convert(a: SourceModel, field2: Any) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2), field2=3) == DestModel(field1=1, field2=3)


@pytest.mark.parametrize('way', FactoryWay.params())
def test_downcast(src_model_spec, dst_model_spec, way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any
        field3: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    if way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(SourceModel(field1=1, field2=2, field3=3)) == DestModel(field1=1, field2=2)


def test_upcast(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any
        field3: Any

    @impl_converter
    def convert(a: SourceModel, field3: Any) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2), field3=3) == DestModel(field1=1, field2=2, field3=3)


@pytest.mark.parametrize('way', FactoryWay.params())
def test_nested(src_model_spec, dst_model_spec, way):
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

    if way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(
        SourceModel(
            field1=1,
            field2=2,
            nested=SourceModelNested(field1=3),
        )
    ) == DestModel(
        field1=1,
        field2=2,
        nested=DestModelNested(field1=3),
    )


@pytest.mark.parametrize('way', FactoryWay.params())
def test_same_nested(src_model_spec, dst_model_spec, way):
    @src_model_spec.decorator
    class SourceModelNested(*src_model_spec.bases):
        field1: Any

    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any
        nested1: SourceModelNested
        nested2: SourceModelNested

    @dst_model_spec.decorator
    class DestModelNested(*dst_model_spec.bases):
        field1: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any
        nested1: DestModelNested
        nested2: DestModelNested

    if way == FactoryWay.IMPL_CONVERTER:
        @impl_converter
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel)

    assert convert(
        SourceModel(
            field1=1,
            field2=2,
            nested1=SourceModelNested(field1=3),
            nested2=SourceModelNested(field1=4),
        )
    ) == DestModel(
        field1=1,
        field2=2,
        nested1=DestModelNested(field1=3),
        nested2=DestModelNested(field1=4),
    )
