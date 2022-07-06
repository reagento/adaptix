from typing import List, TypeVar, Optional, Any, Union

import pytest

from dataclass_factory_30.common import EllipsisType
from dataclass_factory_30.factory import OperatingFactory
from dataclass_factory_30.provider import Provider
from dataclass_factory_30.struct_path import get_path

T = TypeVar("T")


class TestFactory(OperatingFactory):
    def __init__(self, recipe: List[Provider]):
        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return []

    provide = OperatingFactory._provide_from_recipe


def raises_instance(exp_exc: Exception, func, *, path: Union[list, None, EllipsisType] = Ellipsis):
    with pytest.raises(type(exp_exc)) as exc:
        func()
    assert exc.value == exp_exc

    if not isinstance(path, EllipsisType):
        extracted_path = get_path(exc.value)
        if path is None:
            assert extracted_path is None
        else:
            assert extracted_path is not None
            assert list(extracted_path) == list(path)


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f'{p}=False', f'{p}=True']
            )(func)
        return func

    return decorator
