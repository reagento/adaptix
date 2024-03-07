from typing import Any

from adaptix.conversion import coercer, get_converter, impl_converter, link

from .local_helpers import FactoryWay


def test_field_rename(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: Any

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[link("field2_src", "field2_dst")])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[link("field2_src", "field2_dst")])

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst=2)


def test_field_swap(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[link("field1", "field2"), link("field2", "field1")])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[link("field1", "field2"), link("field2", "field1")])

    assert convert(SourceModel(field1=1, field2=2)) == DestModel(field1=2, field2=1)


def test_downcast(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any
        field3: Any

    @impl_converter(recipe=[link("field4", "field3")])
    def convert(a: SourceModel, field4: Any) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2), field4=3) == DestModel(field1=1, field2=2, field3=3)


def test_nested(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModelNested(*src_model_spec.bases):
        field1_src: Any

    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any
        nested: SourceModelNested

    @dst_model_spec.decorator
    class DestModelNested(*dst_model_spec.bases):
        field1_dst: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any
        nested: DestModelNested

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[link("field1_src", "field1_dst")])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[link("field1_src", "field1_dst")])

    assert convert(
        SourceModel(
            field1=1,
            field2=2,
            nested=SourceModelNested(field1_src=3),
        ),
    ) == DestModel(
        field1=1,
        field2=2,
        nested=DestModelNested(field1_dst=3),
    )


def test_nested_several(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModelNested(*src_model_spec.bases):
        field1_src: Any

    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1_src: Any
        field2: Any
        nested: SourceModelNested

    @dst_model_spec.decorator
    class DestModelNested(*dst_model_spec.bases):
        field1_dst: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1_dst: Any
        field2: Any
        nested: DestModelNested

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[link("field1_src", "field1_dst")])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[link("field1_src", "field1_dst")])

    assert convert(
        SourceModel(
            field1_src=1,
            field2=2,
            nested=SourceModelNested(field1_src=3),
        ),
    ) == DestModel(
        field1_dst=1,
        field2=2,
        nested=DestModelNested(field1_dst=3),
    )


def test_coercer(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: int

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: str

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[link("field2_src", "field2_dst", coercer=str)])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[link("field2_src", "field2_dst", coercer=str)])

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst="2")


def test_coercer_priority(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: int

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: str

    recipe = [
        coercer(int, str, func=str),
        link("field2_src", "field2_dst", coercer=lambda x: str(x + 1)),
    ]
    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=recipe)
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=recipe)

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst="3")

