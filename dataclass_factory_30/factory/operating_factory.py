from abc import ABC
from dataclasses import dataclass
from typing import Optional, TypeVar

from ..provider import CannotProvide, Mediator, ParserRequest, Provider, Request, SerializerRequest
from .basic_factory import IncrementalRecipe, ProvidingFromRecipe
from .mediator import RecursionResolving, StubsRecursionResolver


class FuncWrapper:
    __slots__ = ('__call__',)

    def __init__(self):
        self.__call__ = None

    def set_func(self, func):
        self.__call__ = func.__call__


class FuncRecursionResolver(StubsRecursionResolver):
    def get_stub(self, request):
        return FuncWrapper()

    def saturate_stub(self, actual, stub) -> None:
        stub.set_func(actual)


@dataclass
class NoSuitableProvider(Exception):
    important_error: Optional[CannotProvide]

    def __str__(self):
        return repr(self.important_error)


T = TypeVar('T')


class OperatingFactory(IncrementalRecipe, ProvidingFromRecipe, Provider, ABC):
    """A factory that can operate as Factory but have no predefined providers"""

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request, mediator.request_stack)

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request, [])
        except CannotProvide as e:
            important_error = e if e.is_important() else None
            raise NoSuitableProvider(important_error=important_error)

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                ParserRequest: FuncRecursionResolver(),
                SerializerRequest: FuncRecursionResolver(),
            }
        )
