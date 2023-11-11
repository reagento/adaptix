import pytest
from tests_helpers import ByTrailSelector

from adaptix import DebugTrail


@pytest.fixture(params=[False, True], ids=lambda x: f'strict_coercion={x}')
def strict_coercion(request):
    return request.param


@pytest.fixture(params=[DebugTrail.DISABLE, DebugTrail.FIRST, DebugTrail.ALL])
def debug_trail(request):
    return request.param


@pytest.fixture
def trail_select(debug_trail):
    return ByTrailSelector(debug_trail)