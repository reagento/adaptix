import pytest

from adaptix._internal.morphing.model.basic_gen import CodeGenAccumulator


@pytest.fixture()
def accum():
    return CodeGenAccumulator()
