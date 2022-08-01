import pytest

from dataclass_factory_30.provider.model.basic_gen import CodeGenAccumulator
from tests_30.provider.model.common import DebugCtx


@pytest.fixture
def debug_ctx():
    ctx = DebugCtx(CodeGenAccumulator())
    yield ctx


def pytest_make_parametrize_id(config, val, argname):
    return str(val)
