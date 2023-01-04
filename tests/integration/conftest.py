import pytest

from _dataclass_factory.provider.model.basic_gen import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
