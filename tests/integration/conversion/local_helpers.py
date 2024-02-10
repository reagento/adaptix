from enum import Enum

import pytest


class FactoryWay(Enum):
    IMPL_CONVERTER = 'impl_converter'
    GET_CONVERTER = 'get_converter'

    @classmethod
    def params(cls):
        return [pytest.param(way, id=way.value) for way in cls]
