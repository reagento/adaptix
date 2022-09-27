from abc import ABC
from typing import TypeVar

from ..provider import CannotProvide, DumperRequest, LoaderRequest, Mediator, Provider, Request
from .base_retort import BaseRetort
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


class OperatingRetort(BaseRetort, Provider, ABC):
    """A retort that can operate as Retort but have no predefined providers and no high-level user interface"""

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        return self._provide_from_recipe(request, mediator.request_stack[:-1])

    def _facade_provide(self, request: Request[T]) -> T:
        try:
            return self._provide_from_recipe(request, [])
        except CannotProvide:
            # Attaching to traceback only last CannotProvide is very discouraging
            raise NoSuitableProvider from None

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                LoaderRequest: FuncRecursionResolver(),
                DumperRequest: FuncRecursionResolver(),
            }
        )
