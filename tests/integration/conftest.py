import pytest

from dataclass_factory._internal.provider.model.basic_gen import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
