from abc import ABC, abstractmethod
from typing import List, TypeVar, Optional

from .mediator import RecipeSearcher, RawRecipeSearcher, BuiltinMediator, RecursionResolving
from ..provider import Provider, Mediator, Request, CannotProvide


class FullRecipeGetter(ABC):
    @abstractmethod
    def _get_full_recipe(self) -> List[Provider]:
        pass


class IncrementalRecipe(FullRecipeGetter, ABC):
    recipe: List[Provider] = []
    _inc_class_recipe: List[Provider] = []

    def __init_subclass__(cls, **kwargs):
        if 'recipe' in vars(cls):
            cls._inc_class_recipe = cls.recipe + cls._inc_class_recipe

    def __init__(self, recipe: Optional[List[Provider]]):
        if recipe is None:
            recipe = []
        self._inc_fac_instance_recipe = recipe

    @abstractmethod
    def _get_config_recipe(self) -> List[Provider]:
        pass

    def _get_class_recipe(self) -> List[Provider]:
        return self._inc_class_recipe

    def _get_full_recipe(self) -> List[Provider]:
        return self.recipe + self._get_config_recipe() + self._get_class_recipe()


T = TypeVar('T')


class NoSuitableProvider(Exception):
    pass


class ProvidingFromRecipe(FullRecipeGetter, ABC):
    def _get_searcher(self) -> RecipeSearcher:
        return RawRecipeSearcher(recipe=self._get_full_recipe())

    @abstractmethod
    def _get_recursion_resolving(self) -> RecursionResolving:
        pass

    def _create_mediator(self) -> Mediator:
        searcher = self._get_searcher()
        recursion_resolving = self._get_recursion_resolving()
        return BuiltinMediator(searcher, recursion_resolving)

    def _provide_from_recipe(self, request: Request[T]) -> T:
        mediator = self._create_mediator()
        try:
            return mediator.provide(request)
        except CannotProvide:
            raise NoSuitableProvider
