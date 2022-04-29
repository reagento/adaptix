import pytest

from dataclass_factory_30.provider.fields.basic_gen import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
