from typing import List, TypeVar

import pytest

from dataclass_factory_30.factory import OperatingFactory
from dataclass_factory_30.provider import Provider

T = TypeVar("T")


class TestFactory(OperatingFactory):
    def __init__(self, recipe: List[Provider]):
        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return []

    provide = OperatingFactory._provide_from_recipe


def raises_instance(exp_exc: Exception, func):
    with pytest.raises(type(exp_exc)) as exc:
        func()
    assert exc.value == exp_exc


def parametrize_bool(param: str):
    return pytest.mark.parametrize(
        param, [False, True],
        ids=[f'{param}=False', f'{param}=True']
    )
