from typing import Mapping, Optional

from adaptix import Retort, TypeHint
from adaptix._internal.feature_requirement import HAS_PYDANTIC_PKG
from adaptix._internal.provider.request_cls import LocStack, TypeHintLoc
from adaptix._internal.provider.shape_provider import (
    InputShapeRequest,
    OutputShapeRequest,
    provide_generic_resolved_shape,
)
from adaptix._internal.type_tools import is_subclass_soft


def _get_expected(
    tp: TypeHint,
    *,
    expected: Mapping[str, TypeHint],
    pydantic: Optional[Mapping[str, TypeHint]],
) -> Mapping[str, TypeHint]:
    if pydantic is not None and HAS_PYDANTIC_PKG:
        from pydantic import BaseModel
        if is_subclass_soft(tp, BaseModel):
            return pydantic
    return expected


def assert_fields_types(
    tp: TypeHint,
    expected: Mapping[str, TypeHint],
    *,
    pydantic: Optional[Mapping[str, TypeHint]] = None,
) -> None:
    retort = Retort()
    mediator = retort._create_mediator()

    final_expected = _get_expected(tp, expected=expected, pydantic=pydantic)

    input_shape = provide_generic_resolved_shape(
        mediator,
        InputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    input_field_types = {field.id: field.type for field in input_shape.fields}
    assert input_field_types == final_expected

    output_shape = provide_generic_resolved_shape(
        mediator,
        OutputShapeRequest(loc_stack=LocStack(TypeHintLoc(type=tp))),
    )
    output_field_types = {field.id: field.type for field in output_shape.fields}
    assert output_field_types == final_expected
