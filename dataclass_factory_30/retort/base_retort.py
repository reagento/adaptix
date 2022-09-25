from abc import ABC, ABCMeta, abstractmethod
from typing import ClassVar, List, Optional, Sequence, TypeVar

from ..provider import Mediator, Provider, Request
from .mediator import BuiltinMediator, RawRecipeSearcher, RecipeSearcher, RecursionResolving
from .utils import Cloneable, ForbiddingDescriptor


class RetortMeta(ABCMeta):  # inherits from ABCMeta to be compatible with ABC
    _own_class_recipe: List[Provider]
    recipe = ForbiddingDescriptor()

    def __new__(mcs, name, bases, namespace, **kwargs):
        _cls_recipe = namespace.get('recipe', [])

        if not isinstance(_cls_recipe, list) or not all(isinstance(el, Provider) for el in _cls_recipe):
            raise TypeError("Recipe attributes must be List[Provider]")

        namespace['_own_class_recipe'] = _cls_recipe.copy()
        namespace['recipe'] = ForbiddingDescriptor()
        return super().__new__(mcs, name, bases, namespace, **kwargs)


T = TypeVar('T')


class BaseRetort(Cloneable, ABC, metaclass=RetortMeta):
    recipe: List[Provider] = []
    _full_class_recipe: ClassVar[List[Provider]]

    def __init_subclass__(cls, **kwargs):
        # noinspection PyProtectedMember
        recipe_sum = sum(
            (
                parent._own_class_recipe  # pylint: disable=E1101
                for parent in cls.mro()
                if isinstance(parent, RetortMeta)
            ),
            start=[],
        )
        cls._full_class_recipe = recipe_sum

    def __init__(self, recipe: Optional[List[Provider]]):
        self._inc_instance_recipe = recipe or []
        self._calculate_derived()

    @abstractmethod
    def _get_config_recipe(self) -> List[Provider]:
        ...

    def _get_full_recipe(self) -> List[Provider]:
        return self._full_recipe

    def _calculate_derived(self):
        super()._calculate_derived()
        self._full_recipe = (
            self._inc_instance_recipe
            + self._get_config_recipe()
            + self._full_class_recipe
        )

    def _get_searcher(self) -> RecipeSearcher:
        return RawRecipeSearcher(recipe=self._get_full_recipe())

    @abstractmethod
    def _get_recursion_resolving(self) -> RecursionResolving:
        ...

    def _create_mediator(self, request_stack: Sequence[Request]) -> Mediator:
        searcher = self._get_searcher()
        recursion_resolving = self._get_recursion_resolving()
        return BuiltinMediator(searcher, recursion_resolving, request_stack)

    def _provide_from_recipe(self, request: Request[T], request_stack: Sequence[Request]) -> T:
        """Process request iterating over the result of _get_full_recipe()
        :param request:
        :return: request result
        :raise CannotProvide: request did not processed
        """
        mediator = self._create_mediator(request_stack)
        return mediator.provide(request)
