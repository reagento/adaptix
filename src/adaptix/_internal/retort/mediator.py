from abc import ABC, abstractmethod
from itertools import islice
from typing import Any, Callable, Dict, Generic, Iterable, List, Sequence, Set, Tuple, Type, TypeVar

from ..common import TypeHint
from ..datastructures import ClassDispatcher
from ..essential import CannotProvide, Mediator, Provider, Request
from ..provider.provider_wrapper import RequestClassDeterminedProvider
from ..provider.request_filtering import ExactOriginMergedProvider, ExactOriginRC, ProviderWithRC

T = TypeVar('T')


class StubsRecursionResolver(ABC, Generic[T]):
    @abstractmethod
    def create_stub(self, request: Request[T]) -> T:
        ...

    @abstractmethod
    def saturate_stub(self, actual: T, stub: T) -> None:
        ...


ProvideCallable = Callable[[Mediator, Request[T]], T]
SearchResult = Tuple[ProvideCallable[T], int]


class RecipeSearcher(ABC):
    """An object that implements iterating over recipe list.

    An offset of each element must belong to [0; max_offset)
    """

    @abstractmethod
    def search_candidates(self, search_offset: int, request: Request[T]) -> Iterable[SearchResult[T]]:
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
        self._sent_request: Set[Request] = set()
        self.next_offset = 0
        self.recursion_stubs: Dict[Request, Any] = {}

    def provide(self, request: Request[T], *, extra_stack: Sequence[Request[Any]] = ()) -> T:
        if request in self._sent_request:  # maybe we need to lookup in set for large request_stack
            if request in self.recursion_stubs:
                return self.recursion_stubs[request]
            try:
                resolver = self._get_resolver(request)
            except KeyError:
                raise RecursionError("Infinite recursion has been detected that can not be resolved") from None

            stub = resolver.create_stub(request)
            self.recursion_stubs[request] = stub
            return stub

        self._request_stack.extend(extra_stack)
        self._request_stack.append(request)
        self._sent_request.add(request)
        try:
            result = self._provide_non_recursive(request, 0)
        finally:
            del self._request_stack[-1 - len(extra_stack):]
            self._sent_request.discard(request)

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
            except CannotProvide as e:
                if e.is_terminal:
                    self.next_offset = init_next_offset
                    raise e
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


class Combiner(ABC):
    @abstractmethod
    def add_element(self, provider: Provider) -> bool:
        ...

    @abstractmethod
    def combine_elements(self) -> Sequence[Provider]:
        ...

    @abstractmethod
    def has_elements(self) -> bool:
        ...


class ExactOriginCombiner(Combiner):
    def __init__(self) -> None:
        self._combo: List[Tuple[ExactOriginRC, Provider]] = []
        self._origins: Set[TypeHint] = set()

    def add_element(self, provider: Provider) -> bool:
        if not isinstance(provider, ProviderWithRC):
            return False
        request_checker = provider.get_request_checker()
        if request_checker is None:
            return False
        if not isinstance(request_checker, ExactOriginRC):
            return False
        if request_checker.origin in self._origins:
            return False

        self._combo.append((request_checker, provider))
        self._origins.add(request_checker.origin)
        return True

    def combine_elements(self) -> Sequence[Provider]:
        if len(self._combo) == 1:
            return [self._combo[0][1]]

        merged_provider = ExactOriginMergedProvider(self._combo)
        self._combo.clear()
        self._origins.clear()
        return [merged_provider]

    def has_elements(self) -> bool:
        return bool(self._combo)


class IntrospectingRecipeSearcher(RecipeSearcher):
    def __init__(self, recipe: Sequence[Provider]):
        self._recipe = recipe
        self._cls_to_recipe: Dict[Type[Request], Sequence[Provider]] = {}

    def search_candidates(self, search_offset: int, request: Request) -> Iterable[SearchResult]:
        request_cls = type(request)
        try:
            sub_recipe = self._cls_to_recipe[request_cls]
        except KeyError:
            sub_recipe = self._collect_candidates(request_cls, self._recipe)
            self._cls_to_recipe[request_cls] = sub_recipe

        for i, provider in enumerate(
            islice(sub_recipe, search_offset, None),
            start=search_offset
        ):
            yield provider.apply_provider, i + 1

    def _create_combiner(self) -> Combiner:
        return ExactOriginCombiner()

    def _merge_providers(self, recipe: Sequence[Provider]) -> Sequence[Provider]:
        combiner = self._create_combiner()

        result: List[Provider] = []
        for provider in recipe:
            is_added = combiner.add_element(provider)
            if not is_added:
                if combiner.has_elements():
                    result.extend(combiner.combine_elements())
                result.append(provider)

        if combiner.has_elements():
            result.extend(combiner.combine_elements())
        return result

    def _collect_candidates(self, request_cls: Type[Request], recipe: Sequence[Provider]) -> Sequence[Provider]:
        candidates = [
            provider
            for provider in recipe
            if (
                not isinstance(provider, RequestClassDeterminedProvider)
                or provider.maybe_can_process_request_cls(request_cls)
            )
        ]
        return self._merge_providers(candidates)

    def clear_cache(self):
        self._cls_to_recipe = {}

    def get_max_offset(self) -> int:
        return len(self._recipe)
