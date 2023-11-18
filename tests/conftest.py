import pytest
from tests_helpers import ByTrailSelector

from adaptix import DebugTrail
from adaptix._internal.feature_requirement import HAS_PY_312


@pytest.fixture(params=[False, True], ids=lambda x: f'strict_coercion={x}')
def strict_coercion(request):
    return request.param


@pytest.fixture(params=[DebugTrail.DISABLE, DebugTrail.FIRST, DebugTrail.ALL])
def debug_trail(request):
    return request.param


@pytest.fixture
def trail_select(debug_trail):
    return ByTrailSelector(debug_trail)


collect_ignore_glob = [] if HAS_PY_312 else ['*_312.py']
