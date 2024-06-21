from typing import Mapping, Optional

from adaptix import Retort, TypeHint
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.location import TypeHintLoc
from adaptix._internal.provider.shape_provider import (
    InputShapeRequest,
    OutputShapeRequest,
    provide_generic_resolved_shape,
)
from adaptix._internal.type_tools import is_pydantic_class


def assert_distinct_fields_types(
    tp: TypeHint,
    *,
    input: Mapping[str, TypeHint],  # noqa: A002
    output: Mapping[str, TypeHint],
) -> None:
    retort = Retort()
    mediator = retort._create_mediator()

    input_shape = provide_generic_resolved_shape(
        mediator,
        InputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    input_field_types = {field.id: field.type for field in input_shape.fields}
    assert input_field_types == input

    output_shape = provide_generic_resolved_shape(
        mediator,
        OutputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    output_field_types = {field.id: field.type for field in output_shape.fields}
    assert output_field_types == output


def assert_fields_types(
    tp: TypeHint,
    expected: Mapping[str, TypeHint],
    *,
    pydantic: Optional[Mapping[str, TypeHint]] = None,
) -> None:
    final_expected = pydantic if pydantic is not None and is_pydantic_class(tp) else expected
    assert_distinct_fields_types(
        tp,
        input=final_expected,
        output=final_expected,
    )
