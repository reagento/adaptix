from abc import ABC, ABCMeta, abstractmethod
from typing import ClassVar, Iterable, Optional, Sequence, TypeVar

from ..common import VarTuple
from ..provider import Mediator, Provider, Request
from ..utils import Cloneable, ForbiddingDescriptor
from .mediator import BuiltinMediator, RawRecipeSearcher, RecipeSearcher, RecursionResolving


class RetortMeta(ABCMeta):  # inherits from ABCMeta to be compatible with ABC
    _own_class_recipe: VarTuple[Provider]
    recipe = ForbiddingDescriptor()

    def __new__(mcs, name, bases, namespace, **kwargs):
        try:
            _cls_recipe = tuple(namespace.get('recipe', []))
        except TypeError:
            raise TypeError("Recipe attributes must be Iterable[Provider]") from None

        if not all(isinstance(el, Provider) for el in _cls_recipe):
            raise TypeError("Recipe attributes must be Iterable[Provider]")

        namespace['_own_class_recipe'] = _cls_recipe
        namespace['recipe'] = ForbiddingDescriptor()
        return super().__new__(mcs, name, bases, namespace, **kwargs)


T = TypeVar('T')


class BaseRetort(Cloneable, ABC, metaclass=RetortMeta):
    recipe: Iterable[Provider] = []
    _full_class_recipe: ClassVar[VarTuple[Provider]]

    def __init_subclass__(cls, **kwargs):
        # noinspection PyProtectedMember
        recipe_sum = sum(
            (
                parent._own_class_recipe  # pylint: disable=E1101
                for parent in cls.mro()
                if isinstance(parent, RetortMeta)
            ),
            start=(),
        )
        cls._full_class_recipe = recipe_sum

    def __init__(self, recipe: Optional[Iterable[Provider]]):
        self._inc_instance_recipe = () if recipe is None else tuple(recipe)
        self._calculate_derived()

    @abstractmethod
    def _get_config_recipe(self) -> VarTuple[Provider]:
        ...

    def _get_full_recipe(self) -> Sequence[Provider]:
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
        :raise CannotProvide: request was not processed
        """
        mediator = self._create_mediator(request_stack)
        return mediator.provide(request)
