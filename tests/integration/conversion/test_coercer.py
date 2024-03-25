import typing
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Set, Tuple, Union

import pytest
from tests_helpers import cond_list

from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix.conversion import coercer, impl_converter


@pytest.mark.parametrize(
    "func",
    [
        pytest.param(int, id="int"),
        pytest.param(lambda x: int(x), id="lambda"),
    ],
)
def test_simple(model_spec, func):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: str
        field2: str

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: int

    @impl_converter(recipe=[coercer(str, int, func=func)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1=1, field2=2)


def test_model_priority(model_spec):
    @model_spec.decorator
    class SourceModelNested(*model_spec.bases):
        field1: Any

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: Any
        field2: Any
        nested: SourceModelNested

    @model_spec.decorator
    class DestModelNested(*model_spec.bases):
        field1: Any

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: Any
        field2: Any
        nested: DestModelNested

    def my_coercer(a: SourceModelNested) -> DestModelNested:
        return DestModelNested(field1=model_spec.get_field(a, "field1") + 10)

    @impl_converter(recipe=[coercer(SourceModelNested, DestModelNested, func=my_coercer)])
    def convert(a: SourceModel) -> DestModel:
        ...

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


def test_any_dest(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: str
        field2: str

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: Any
        field2: Any

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1="1", field2="2")


def test_subclass_builtin(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: bool
        field2: bool

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: int

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=False, field2=True)) == DestModel(field1=False, field2=True)


@pytest.mark.parametrize(
    ["src_tp", "dst_tp"],
    [
        pytest.param(int, Optional[int]),
        pytest.param(int, Union[int, str]),
        pytest.param(Union[int, str], Union[int, str, None]),
    ],
)
def test_union_subcase(model_spec, src_tp, dst_tp):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: src_tp

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: dst_tp

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=2)) == DestModel(field1=1, field2=2)


@pytest.mark.parametrize(
    ["src_tp", "dst_tp", "src_value", "dst_value"],
    [
        pytest.param(Optional[int], Optional[int], 10, 10),
        pytest.param(Optional[int], Optional[int], None, None),
        pytest.param(Optional[str], Optional[str], "abc", "abc"),
        pytest.param(Optional[str], Optional[str], None, None),
        pytest.param(Optional[bool], Optional[int], True, True),
        pytest.param(Optional[str], Optional[int], "123", 123),
        *cond_list(
            HAS_ANNOTATED,
            lambda: [
                pytest.param(Optional[typing.Annotated[int, "meta"]], Optional[int], 123, 123),
                pytest.param(Optional[int], Optional[typing.Annotated[int, "meta"]], 123, 123),
                pytest.param(typing.Annotated[Optional[int], "meta"], Optional[int], 123, 123),
                pytest.param(Optional[int], typing.Annotated[Optional[int], "meta"], 123, 123),
            ],
        ),
    ],
)
def test_optional(model_spec, src_tp, dst_tp, src_value, dst_value):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: src_tp

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: dst_tp

    @impl_converter(recipe=[coercer(str, int, func=int)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=src_value)) == DestModel(field1=1, field2=dst_value)


def test_optional_with_model(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: Optional[SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: Optional[DestModelInner]

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2=SourceModelInner(data=2)))
        ==
        DestModel(field1=1, field2=DestModelInner(data=2))
    )
    assert convert(SourceModel(field1=1, field2=None)) == DestModel(field1=1, field2=None)


def test_optional_with_model_and_ctx(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: Optional[SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int
        extra1: str

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: Optional[DestModelInner]

    @impl_converter
    def convert(a: SourceModel, extra1: str) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2=SourceModelInner(data=2)), "e1")
        ==
        DestModel(field1=1, field2=DestModelInner(data=2, extra1="e1"))
    )
    assert convert(SourceModel(field1=1, field2=None), "e1") == DestModel(field1=1, field2=None)


@pytest.mark.parametrize(
    ["src_tp", "dst_tp", "src_value", "dst_value"],
    [
        pytest.param(List[int], List[int], [1, 2, 3], [1, 2, 3]),
        pytest.param(List[str], List[int], ["1", "2", "3"], [1, 2, 3]),
        pytest.param(List[int], Tuple[int, ...], [1, 2, 3], (1, 2, 3)),
        pytest.param(List[str], Tuple[int, ...], ["1", "2", "3"], (1, 2, 3)),
        pytest.param(Set[int], Tuple[int, ...], {1, 2, 3}, (1, 2, 3)),
        pytest.param(List[int], Iterable[int], [1, 2, 3], (1, 2, 3)),
        pytest.param(Iterable[int], Iterable[int], [1, 2, 3], (1, 2, 3)),
    ],
)
def test_iterable(model_spec, src_tp, dst_tp, src_value, dst_value):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: src_tp

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: dst_tp

    @impl_converter(recipe=[coercer(str, int, func=int)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=src_value)) == DestModel(field1=1, field2=dst_value)


def test_iterable_with_model(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: List[SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: List[DestModelInner]

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2=[SourceModelInner(data=1), SourceModelInner(data=2)]))
        ==
        DestModel(field1=1, field2=[DestModelInner(data=1), DestModelInner(data=2)])
    )


def test_iterable_with_model_and_ctx(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: List[SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int
        extra1: str

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: List[DestModelInner]

    @impl_converter
    def convert(a: SourceModel, extra1: str) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2=[SourceModelInner(data=1), SourceModelInner(data=2)]), "e1")
        ==
        DestModel(field1=1, field2=[DestModelInner(data=1, extra1="e1"), DestModelInner(data=2, extra1="e1")])
    )


def test_iterable_on_top_level():
    @impl_converter(recipe=[coercer(str, int, func=int)])
    def convert(a: List[str]) -> List[int]:
        ...

    assert convert(["1", "2", "3"]) == [1, 2, 3]


def test_iterable_of_models_on_top_level(model_spec):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        v: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        v: int

    @impl_converter(recipe=[coercer(str, int, func=int)])
    def convert(a: List[SourceModel]) -> List[DestModel]:
        ...

    assert convert([SourceModel(v=1), SourceModel(v=2)]) == [DestModel(v=1), DestModel(v=2)]


@pytest.mark.parametrize(
    ["src_tp", "dst_tp", "src_value", "dst_value"],
    [
        pytest.param(Dict[int, int], Dict[int, int], {1: 1, 2: 2, 3: 3}, {1: 1, 2: 2, 3: 3}),
        pytest.param(Dict[str, str], Dict[int, int], {"1": "1", "2": "2", "3": "3"}, {1: 1, 2: 2, 3: 3}),
        pytest.param(Mapping[str, str], Dict[int, int], {"1": "1", "2": "2", "3": "3"}, {1: 1, 2: 2, 3: 3}),
        pytest.param(Mapping[str, str], MutableMapping[int, int], {"1": "1", "2": "2", "3": "3"}, {1: 1, 2: 2, 3: 3}),
    ],
)
def test_dict(model_spec, src_tp, dst_tp, src_value, dst_value):
    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: src_tp

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: dst_tp

    @impl_converter(recipe=[coercer(str, int, func=int)])
    def convert(a: SourceModel) -> DestModel:
        ...

    assert convert(SourceModel(field1=1, field2=src_value)) == DestModel(field1=1, field2=dst_value)


def test_dict_with_model(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: Dict[str, SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: Dict[str, DestModelInner]

    @impl_converter
    def convert(a: SourceModel) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2={"a": SourceModelInner(data=1), "b": SourceModelInner(data=2)}))
        ==
        DestModel(field1=1, field2={"a": DestModelInner(data=1), "b": DestModelInner(data=2)})
    )


def test_dict_with_model_and_ctx(model_spec):
    @model_spec.decorator
    class SourceModelInner(*model_spec.bases):
        data: int

    @model_spec.decorator
    class SourceModel(*model_spec.bases):
        field1: int
        field2: Dict[str, SourceModelInner]

    @model_spec.decorator
    class DestModelInner(*model_spec.bases):
        data: int
        extra1: str

    @model_spec.decorator
    class DestModel(*model_spec.bases):
        field1: int
        field2: Dict[str, DestModelInner]

    @impl_converter
    def convert(a: SourceModel, extra1: str) -> DestModel:
        ...

    assert (
        convert(SourceModel(field1=1, field2={"a": SourceModelInner(data=1), "b": SourceModelInner(data=2)}), "e1")
        ==
        DestModel(field1=1, field2={"a": DestModelInner(data=1, extra1="e1"), "b": DestModelInner(data=2, extra1="e1")})
    )
