from abc import ABC, abstractmethod
from itertools import islice
from typing import Any, Callable, Dict, Generic, Iterable, Sequence, Tuple, TypeVar

from ..provider import CannotProvide, Mediator, Provider, Request
from ..utils import ClassDispatcher

T = TypeVar('T')


class StubsRecursionResolver(ABC, Generic[T]):
    @abstractmethod
    def get_stub(self, request: Request[T]) -> T:
        ...

    @abstractmethod
    def saturate_stub(self, actual: T, stub: T) -> None:
        ...


ProvideCallable = Callable[[Mediator, Request[T]], T]
SearchResult = Tuple[ProvideCallable, int]


class RecipeSearcher(ABC):
    """An object that implements iterating over recipe list.

    An offset of each element must belong to [0; max_offset)
    """

    @abstractmethod
    def search_candidates(self, search_offset: int, request: Request) -> Iterable[SearchResult]:
        ...

    @abstractmethod
    def get_max_offset(self) -> int:
        ...

    @abstractmethod
    def clear_cache(self):
        ...


RecursionResolving = ClassDispatcher[Request, StubsRecursionResolver]


class BuiltinMediator(Mediator):
    def __init__(
        self,
        searcher: RecipeSearcher,
        recursion_resolving: RecursionResolving,
        request_stack: Sequence[Request[Any]],
    ):
        self.searcher = searcher
        self.recursion_resolving = recursion_resolving

        self._request_stack = list(request_stack)
        self.next_offset = 0
        self.recursion_stubs: Dict[Request, Any] = {}

    def provide(self, request: Request[T]) -> T:
        if request in self._request_stack:  # maybe we need to lookup in set for large request_stack
            try:
                resolver = self._get_resolver(request)
            except KeyError:
                raise RecursionError("Infinite recursion has been detected that can not be resolved") from None

            stub = resolver.get_stub(request)
            self.recursion_stubs[request] = stub
            return stub

        self._request_stack.append(request)
        try:
            result = self._provide_non_recursive(request, 0)
        finally:
            self._request_stack.pop(-1)

        if request in self.recursion_stubs:
            resolver = self._get_resolver(request)
            stub = self.recursion_stubs.pop(request)
            resolver.saturate_stub(result, stub)

        return result

    def provide_from_next(self) -> Any:
        return self._provide_non_recursive(self._request_stack[-1], self.next_offset)

    @property
    def request_stack(self) -> Sequence[Request[Any]]:
        return self._request_stack.copy()

    def _get_resolver(self, request: Request) -> StubsRecursionResolver:
        return self.recursion_resolving.dispatch(type(request))

    def _provide_non_recursive(self, request: Request[T], search_offset: int) -> T:
        init_next_offset = self.next_offset
        for provide_callable, next_offset in self.searcher.search_candidates(
            search_offset, request
        ):
            self.next_offset = next_offset
            try:
                result = provide_callable(self, request)
            except CannotProvide:
                continue

            self.next_offset = init_next_offset
            return result

        raise CannotProvide


class RawRecipeSearcher(RecipeSearcher):
    def __init__(self, recipe: Sequence[Provider]):
        self.recipe = recipe

    def search_candidates(self, search_offset: int, request: Request) -> Iterable[SearchResult]:
        for i, provider in enumerate(
            islice(self.recipe, search_offset, None),
            start=search_offset
        ):
            yield provider.apply_provider, i + 1

    def clear_cache(self):
        pass

    def get_max_offset(self) -> int:
        return len(self.recipe)
