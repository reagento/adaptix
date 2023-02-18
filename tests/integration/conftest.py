import pytest

from adaptix._internal.provider.model.basic_gen import CodeGenAccumulator


@pytest.fixture
def accum():
    return CodeGenAccumulator()
