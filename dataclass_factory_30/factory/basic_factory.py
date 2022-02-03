from abc import ABC, abstractmethod
from typing import List, TypeVar, Optional, ClassVar

from .mediator import RecipeSearcher, RawRecipeSearcher, BuiltinMediator, RecursionResolving
from ..provider import Provider, Mediator, Request


class FullRecipeGetter(ABC):
    @abstractmethod
    def _get_full_recipe(self) -> List[Provider]:
        pass


class IncrementalRecipe(FullRecipeGetter, ABC):
    """A base class defining building of full recipe.
    Full recipe is sum of instance recipe, config recipe and class recipe.

    Instance recipe is setting up at `recipe` constructor parameter.

    Config recipe is creating with :method:`_get_config_recipe()`.
    It can be used to passing factory config attributes to recipe.

    Class recipe is a sum of `recipe` attribute of class and class recipe of parents.
    """
    recipe: List[Provider] = []
    _inc_class_recipe: ClassVar[List[Provider]] = []

    def __init_subclass__(cls, **kwargs):
        parent_recipe = sum(
            (
                parent._inc_class_recipe
                for parent in cls.__bases__
                if issubclass(parent, IncrementalRecipe)
            ),
            start=[],
        )

        class_own_recipe = cls.recipe if 'recipe' in vars(cls) else []

        cls._inc_class_recipe = class_own_recipe + parent_recipe

    def __init__(self, recipe: Optional[List[Provider]]):
        if recipe is None:
            recipe = []
        self._inc_instance_recipe = recipe

    @abstractmethod
    def _get_config_recipe(self) -> List[Provider]:
        pass

    def _get_full_recipe(self) -> List[Provider]:
        return (
            self._inc_instance_recipe
            + self._get_config_recipe()
            + self._inc_class_recipe
        )


T = TypeVar('T')


class ProvidingFromRecipe(FullRecipeGetter, ABC):
    """A base class defining providing process from full recipe"""

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
        """Process request iterating over the result of _get_full_recipe()
        :param request:
        :return: request result
        :raise CannotProvide: request did not processed
        """
        mediator = self._create_mediator()
        return mediator.provide(request)
