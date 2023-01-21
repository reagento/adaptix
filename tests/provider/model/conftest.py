import pytest

from dataclass_factory._internal.provider.model.basic_gen import CodeGenAccumulator
from tests_helpers import DebugCtx


@pytest.fixture
def debug_ctx():
    ctx = DebugCtx(CodeGenAccumulator())
    yield ctx


def pytest_make_parametrize_id(config, val, argname):
    return str(val)


@pytest.fixture(params=[False, True], ids=['debug_path=False', 'debug_path=True'])
def debug_path(request):
    return request.param
