from typing import Any

from adaptix._internal.conversion.facade.provider import link_constant
from adaptix.conversion import coercer, impl_converter, link


def test_field_rename(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: Any

    @impl_converter(recipe=[link("field2_src", "field2_dst")])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst=2)


def test_field_swap(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: Any

    @impl_converter(recipe=[link("field1", "field2"), link("field2", "field1")])
    def convert(a: SourceModel) -> DestModel:
        ...

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


def test_nested(src_model_spec, dst_model_spec):
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

    @impl_converter(recipe=[link("field1_src", "field1_dst")])
    def convert(a: SourceModel) -> DestModel:
        ...

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


def test_nested_several(src_model_spec, dst_model_spec):
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

    @impl_converter(recipe=[link("field1_src", "field1_dst")])
    def convert(a: SourceModel) -> DestModel:
        ...

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


def test_coercer(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: int

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: str

    @impl_converter(recipe=[link("field2_src", "field2_dst", coercer=str)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst="2")


def test_coercer_priority(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any
        field2_src: int

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2_dst: str

    @impl_converter(
        recipe=[
            coercer(int, str, func=str),
            link("field2_src", "field2_dst", coercer=lambda x: str(x + 1)),
        ],
    )
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2_src=2)) == DestModel(field1=1, field2_dst="3")


def test_link_to_constant_value(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: str

    @impl_converter(recipe=[link_constant("field2", value="abc")])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1)) == DestModel(field1=1, field2="abc")


def test_link_to_constant_factory(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: Any

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: Any
        field2: list

    @impl_converter(recipe=[link_constant("field2", factory=list)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1)) == DestModel(field1=1, field2=[])
