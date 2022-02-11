import pytest

from dataclass_factory_30.provider.fields_parser import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
