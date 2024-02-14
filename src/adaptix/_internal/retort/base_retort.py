from abc import ABC, ABCMeta, abstractmethod
from typing import ClassVar, Iterable, Sequence, TypeVar

from ..common import VarTuple
from ..provider.essential import Mediator, Provider, Request
from ..utils import Cloneable, ForbiddingDescriptor
from .mediator import BuiltinMediator, ErrorRepresentor, RecursionResolver
from .routing import IntrospectingRecipeSearcher, RecipeSearcher


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

    def __init__(self, recipe: Iterable[Provider] = ()):
        self._inc_instance_recipe = tuple(recipe)
        self._calculate_derived()

    def _get_config_recipe(self) -> VarTuple[Provider]:
        return ()

    def _get_full_recipe(self) -> Sequence[Provider]:
        return self._full_recipe

    def _calculate_derived(self) -> None:
        super()._calculate_derived()
        self._full_recipe = (
            self._inc_instance_recipe
            + self._get_config_recipe()
            + self._full_class_recipe
        )
        self._searcher = self._create_searcher(self._full_recipe)

    def _create_searcher(self, full_recipe: Sequence[Provider]) -> RecipeSearcher:
        return IntrospectingRecipeSearcher(full_recipe)

    @abstractmethod
    def _create_recursion_resolver(self) -> RecursionResolver:
        ...

    @abstractmethod
    def _get_error_representor(self) -> ErrorRepresentor:
        ...

    def _create_mediator(self) -> Mediator:
        recursion_resolver = self._create_recursion_resolver()
        error_representor = self._get_error_representor()
        return BuiltinMediator(
            self._searcher,
            recursion_resolver,
            error_representor,
        )

    def _provide_from_recipe(self, request: Request[T]) -> T:
        """Process request iterating over the result of _get_full_recipe()
        :param request:
        :return: request result
        :raise CannotProvide: request was not processed
        """
        mediator = self._create_mediator()
        return mediator.provide(request)
