from abc import ABC, abstractmethod
from typing import final, List

from . import StaticProvider
from .incremental_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import RecursionResolving
from ..core import Provider


class MultiInheritanceFactory(IncrementalRecipe, ProvidingFromRecipe, ABC):
    @abstractmethod
    def _get_raw_config_recipe(self) -> List[Provider]:
        pass

    @final
    def _get_config_recipe(self) -> List[Provider]:
        result = []
        for base in type(self).__bases__:
            if issubclass(base, MultiInheritanceFactory):
                result.extend(
                    base._get_config_recipe(self)
                )

        return result

    @abstractmethod
    def _get_raw_recursion_resolving(self) -> RecursionResolving:
        pass

    @final
    def _get_recursion_resolving(self) -> RecursionResolving:
        result = {}
        for base in type(self).__bases__:
            if issubclass(base, MultiInheritanceFactory):
                result.update(base._get_raw_recursion_resolving(self).to_dict())

        return RecursionResolving(result)


class BuiltinFactory(MultiInheritanceFactory, StaticProvider, ABC):
    recipe = []
