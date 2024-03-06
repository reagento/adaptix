import pytest
from tests_helpers import pretty_typehint_test_id

from .local_helpers import FactoryWay


@pytest.fixture(params=FactoryWay.params())
def factory_way(request):
    return request.param


pytest_make_parametrize_id = pretty_typehint_test_id
