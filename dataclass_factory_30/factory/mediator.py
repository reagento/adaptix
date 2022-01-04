from abc import ABC, abstractmethod
from itertools import islice
from typing import TypeVar, Set, List, Generic, Dict, Any, Iterable, Tuple, Callable

from ..provider import Request, Provider, Mediator, ClassDispatcher, CannotProvide

T = TypeVar('T')


class StubsRecursionResolver(ABC, Generic[T]):
    @abstractmethod
    def get_stub(self, request: Request[T]) -> T:
        pass

    @abstractmethod
    def saturate_stub(self, actual: T, stub: T) -> None:
        pass


ProvideCallable = Callable[[Mediator, Request[T]], T]

SearchResult = Tuple[ProvideCallable, int]


class RecipeSearcher(ABC):
    """An offset of each element must belong to [0; max_offset)"""

    @abstractmethod
    def search_candidates(self, search_offset: int, request: Request) -> Iterable[SearchResult]:
        pass

    @abstractmethod
    def get_max_offset(self) -> int:
        pass

    @abstractmethod
    def clear_cache(self):
        pass


RecursionResolving = ClassDispatcher[Request, StubsRecursionResolver]


class BuiltinMediator(Mediator):
    def __init__(
        self,
        searcher: RecipeSearcher,
        recursion_resolving: RecursionResolving
    ):
        self.searcher = searcher
        self.recursion_resolving = recursion_resolving

        self.provided_request: Set[Request] = set()
        self.next_offset = 0
        self.recursion_stubs: Dict[Request, Any] = {}

    def provide(self, request: Request[T]) -> T:
        return self._provide(request, 0)

    def provide_from_next(self, request: Request[T]) -> T:
        return self._provide(request, self.next_offset)

    def _get_resolver(self, request: Request) -> StubsRecursionResolver:
        return self.recursion_resolving.dispatch(type(request))

    def _provide(self, request: Request[T], search_offset: int) -> T:
        if request in self.provided_request:
            resolver = self._get_resolver(request)
            stub = resolver.get_stub(request)
            self.recursion_stubs[request] = stub
            return stub

        else:
            result = self._provide_non_recursive(request, search_offset)

            if request in self.recursion_stubs:
                resolver = self._get_resolver(request)
                stub = self.recursion_stubs.pop(request)
                resolver.saturate_stub(result, stub)

            return result

    def _provide_non_recursive(self, request: Request[T], search_offset: int) -> T:
        init_next_offset = self.next_offset
        for provide_callable, next_offset in self.searcher.search_candidates(
            search_offset, request
        ):
            self.provided_request.add(request)  # request mustn't be in set
            self.next_offset = next_offset
            try:
                result = provide_callable(self, request)
            except CannotProvide:
                continue
            finally:
                self.provided_request.remove(request)

            self.next_offset = init_next_offset
            return result

        raise CannotProvide


class RawRecipeSearcher(RecipeSearcher):
    def __init__(self, recipe: List[Provider]):
        self.recipe = recipe

    def search_candidates(self, search_offset: int, request: Request) -> Iterable[SearchResult]:
        for i, provider in enumerate(
            islice(self.recipe, search_offset),
            start=search_offset
        ):
            yield provider.apply_provider, i + 1

    def clear_cache(self):
        pass

    def get_max_offset(self) -> int:
        return len(self.recipe)
