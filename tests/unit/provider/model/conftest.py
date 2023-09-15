import pytest

from adaptix._internal.provider.model.basic_gen import CodeGenAccumulator
from tests_helpers import DebugCtx


@pytest.fixture
def debug_ctx():
    ctx = DebugCtx(CodeGenAccumulator())
    yield ctx


def pytest_make_parametrize_id(config, val, argname):
    return str(val)
