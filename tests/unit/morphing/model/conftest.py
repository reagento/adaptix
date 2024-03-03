import pytest
from tests_helpers import DebugCtx

from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator


@pytest.fixture()
def debug_ctx():
    return DebugCtx(CodeGenAccumulator())


def pytest_make_parametrize_id(config, val, argname):
    return str(val)
