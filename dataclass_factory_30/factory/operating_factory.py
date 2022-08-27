from abc import ABC
from typing import TypeVar

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


class NoSuitableProvider(Exception):
    pass


T = TypeVar('T')


class OperatingFactory(IncrementalRecipe, ProvidingFromRecipe, Provider, ABC):
    """A factory that can operate as Factory but have no predefined providers"""

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request, mediator.request_stack)

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request, [])
        except CannotProvide:
            # Attaching to traceback only last CannotProvide is very discouraging
            raise NoSuitableProvider from None

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                ParserRequest: FuncRecursionResolver(),
                SerializerRequest: FuncRecursionResolver(),
            }
        )
