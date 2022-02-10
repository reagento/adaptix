from typing import List, TypeVar

from dataclass_factory_30.factory import OperatingFactory
from dataclass_factory_30.provider import Provider

T = TypeVar("T")


class TestFactory(OperatingFactory):
    def __init__(self, recipe: List[Provider]):
        super().__init__(recipe)

    def _get_config_recipe(self) -> List[Provider]:
        return []

    provide = OperatingFactory._provide_from_recipe
