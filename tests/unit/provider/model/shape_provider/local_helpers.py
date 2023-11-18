from dataclasses import dataclass
from typing import Any, Mapping

import pytest
from tests_helpers import cond_list

from adaptix import Retort, TypeHint
from adaptix._internal.feature_requirement import HAS_ATTRS_PKG, HAS_PY_311
from adaptix._internal.provider.model.definitions import InputShapeRequest, OutputShapeRequest
from adaptix._internal.provider.model.shape_provider import provide_generic_resolved_shape
from adaptix._internal.provider.request_cls import LocMap, TypeHintLoc


def assert_fields_types(tp: TypeHint, expected: Mapping[str, TypeHint]) -> None:
    retort = Retort()
    mediator = retort._create_mediator(request_stack=())

    input_shape = provide_generic_resolved_shape(
        mediator,
        InputShapeRequest(loc_map=LocMap(TypeHintLoc(type=tp))),
    )
    input_field_types = {field.id: field.type for field in input_shape.fields}
    assert input_field_types == expected

    output_shape = provide_generic_resolved_shape(
        mediator,
        OutputShapeRequest(loc_map=LocMap(TypeHintLoc(type=tp))),
    )
    output_field_types = {field.id: field.type for field in output_shape.fields}
    assert output_field_types == expected


@dataclass
class ModelSpec:
    decorator: Any
    bases: Any


DEFAULT_MODEL_SPEC_PARAMS = (
    'dataclass',
    *cond_list(
        HAS_PY_311,
        [
            'typed_dict',
            'named_tuple',
        ],
    ),
    *cond_list(
        HAS_ATTRS_PKG,
        [
            'attrs',
        ],
    ),
)


def exclude_model_spec(first_spec: str, *other_specs: str):
    specs = [first_spec, *other_specs]

    def decorator(func):
        return pytest.mark.parametrize(
            'model_spec',
            [
                spec
                for spec in DEFAULT_MODEL_SPEC_PARAMS
                if spec not in specs
            ],
            indirect=True
        )(func)

    return decorator
