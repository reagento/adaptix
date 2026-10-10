import pytest
from tests_helpers import DebugCtx

from adaptix import CodeGenBackend
from adaptix._internal.code_tools.x86_64_compiler import check_native_platform
from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator


@pytest.fixture(params=list(CodeGenBackend))
def codegen_backend(request):
    if request.param == CodeGenBackend.X86_64:
        try:
            check_native_platform()
        except RuntimeError as error:
            pytest.skip(str(error))
    return request.param


@pytest.fixture
def debug_ctx():
    return DebugCtx(CodeGenAccumulator())


def pytest_make_parametrize_id(config, val, argname):
    return str(val)
