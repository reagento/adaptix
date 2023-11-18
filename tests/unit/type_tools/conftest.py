from typing import Union

import pytest
from tests_helpers import pretty_typehint_test_id

from adaptix._internal.feature_requirement import HAS_TYPE_UNION_OP

from .local_helpers import UnionOpMaker

pytest_make_parametrize_id = pretty_typehint_test_id


@pytest.fixture(params=[Union, UnionOpMaker()] if HAS_TYPE_UNION_OP else [Union])
def make_union(request):
    return request.param
