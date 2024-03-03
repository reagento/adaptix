import pytest
from tests_helpers import ByTrailSelector, ModelSpecSchema, parametrize_model_spec

from adaptix import DebugTrail
from adaptix._internal.feature_requirement import HAS_PY_312


@pytest.fixture(params=[False, True], ids=lambda x: f"strict_coercion={x}")
def strict_coercion(request):
    return request.param


@pytest.fixture(params=[DebugTrail.DISABLE, DebugTrail.FIRST, DebugTrail.ALL])
def debug_trail(request):
    return request.param


@pytest.fixture()
def trail_select(debug_trail):
    return ByTrailSelector(debug_trail)


@pytest.fixture()
def model_spec() -> ModelSpecSchema:  # noqa: PT004
    ...


@pytest.fixture()
def src_model_spec() -> ModelSpecSchema:  # noqa: PT004
    ...


@pytest.fixture()
def dst_model_spec() -> ModelSpecSchema:  # noqa: PT004
    ...


def pytest_generate_tests(metafunc):
    parametrize_model_spec("model_spec", metafunc)
    parametrize_model_spec("src_model_spec", metafunc)
    parametrize_model_spec("dst_model_spec", metafunc)


collect_ignore_glob = [] if HAS_PY_312 else ["*_312.py"]
