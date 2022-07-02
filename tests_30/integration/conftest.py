import pytest

from dataclass_factory_30.provider.model.basic_gen import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
