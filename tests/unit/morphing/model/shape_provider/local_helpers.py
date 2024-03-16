from typing import Mapping

from adaptix import Retort, TypeHint
from adaptix._internal.provider.request_cls import LocStack, TypeHintLoc
from adaptix._internal.provider.shape_provider import (
    InputShapeRequest,
    OutputShapeRequest,
    provide_generic_resolved_shape,
)


def assert_fields_types(tp: TypeHint, expected: Mapping[str, TypeHint]) -> None:
    retort = Retort()
    mediator = retort._create_mediator()

    input_shape = provide_generic_resolved_shape(
        mediator,
        InputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    input_field_types = {field.id: field.type for field in input_shape.fields}
    assert input_field_types == expected

    output_shape = provide_generic_resolved_shape(
        mediator,
        OutputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    output_field_types = {field.id: field.type for field in output_shape.fields}
    assert output_field_types == expected
