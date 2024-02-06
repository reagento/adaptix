import pytest

from .local_helpers import FactoryWay


@pytest.fixture(params=FactoryWay.params())
def factory_way(request):
    return request.param
