from dataclasses import dataclass
from typing import NamedTuple, TypedDict

import pytest
from tests_helpers import pretty_typehint_test_id

from .local_helpers import DEFAULT_MODEL_SPEC_PARAMS, ModelSpec

pytest_make_parametrize_id = pretty_typehint_test_id


@pytest.fixture(params=DEFAULT_MODEL_SPEC_PARAMS)
def model_spec(request):
    if request.param == 'dataclass':
        return ModelSpec(decorator=dataclass, bases=())
    if request.param == 'typed_dict':
        return ModelSpec(decorator=lambda x: x, bases=(TypedDict,))
    if request.param == 'named_tuple':
        return ModelSpec(decorator=lambda x: x, bases=(NamedTuple,))
    if request.param == 'attrs':
        from attrs import define
        return ModelSpec(decorator=define, bases=())
    raise ValueError
