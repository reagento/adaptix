from dataclasses import dataclass
from typing import Any

from adaptix.conversion import impl_converter


def test_copy(accum):
    @dataclass
    class ExampleAny:
        field1: Any
        field2: Any

    @impl_converter
    def copy(a: ExampleAny) -> ExampleAny:
        ...

    obj1 = ExampleAny(field1=1, field2=2)
    assert copy(obj1) == obj1
    assert copy(obj1) is not obj1


def test_same_shape(accum):
    @dataclass
    class SourceModel:
        field1: Any
        field2: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2)) == DestModel(field1=1, field2=2)


def test_replace(accum):
    @dataclass
    class SourceModel:
        field1: Any
        field2: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any

    @impl_converter
    def convert(a: SourceModel, field2: Any) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2), field2=3) == DestModel(field1=1, field2=3)


def test_downcast(accum):
    @dataclass
    class SourceModel:
        field1: Any
        field2: Any
        field3: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2, field3=3)) == DestModel(field1=1, field2=2)


def test_upcast(accum):
    @dataclass
    class SourceModel:
        field1: Any
        field2: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any
        field3: Any

    @impl_converter
    def convert(a: SourceModel, field3: Any) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2), field3=3) == DestModel(field1=1, field2=2, field3=3)


def test_nested(accum):
    @dataclass
    class SourceModelNested:
        field1: Any

    @dataclass
    class SourceModel:
        field1: Any
        field2: Any
        nested: SourceModelNested

    @dataclass
    class DestModelNested:
        field1: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any
        nested: DestModelNested

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

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


def test_same_nested(accum):
    @dataclass
    class SourceModelNested:
        field1: Any

    @dataclass
    class SourceModel:
        field1: Any
        field2: Any
        nested1: SourceModelNested
        nested2: SourceModelNested

    @dataclass
    class DestModelNested:
        field1: Any

    @dataclass
    class DestModel:
        field1: Any
        field2: Any
        nested1: DestModelNested
        nested2: DestModelNested

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

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
