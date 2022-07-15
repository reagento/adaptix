from abc import ABC

from ..provider import ParserRequest, SerializerRequest
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


class OperatingFactory(IncrementalRecipe, ProvidingFromRecipe, ABC):
    """A factory that can operate as Factory but have no predefined providers"""

    def _get_recursion_resolving(self) -> RecursionResolving:
        return RecursionResolving(
            {
                ParserRequest: FuncRecursionResolver(),
                SerializerRequest: FuncRecursionResolver(),
            }
        )
