from abc import ABC, abstractmethod
from itertools import islice
from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, Sequence, Set, Tuple, Type, TypeVar

from ..common import TypeHint
from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from ..provider.provider_wrapper import RequestClassDeterminedProvider
from ..provider.request_filtering import ExactOriginMergedProvider, ExactOriginRC, ProviderWithRC
from ..utils import add_note

T = TypeVar('T')


class RecursionResolver(ABC, Generic[T]):
    @abstractmethod
    def process_recursion(self, request: Request[T]) -> Optional[Any]:
        ...

    @abstractmethod
    def process_request_result(self, request: Request[T], result: T) -> None:
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


E = TypeVar('E', bound=Exception)


class ErrorRepresentor(ABC):
    @abstractmethod
    def get_no_provider_description(self, request: Request) -> str:
        ...

    @abstractmethod
    def get_request_context_notes(self, request: Request) -> Iterable[str]:
        ...


class BuiltinMediator(Mediator):
    def __init__(
        self,
        searcher: RecipeSearcher,
        recursion_resolver: RecursionResolver,
        error_representor: ErrorRepresentor,
    ):
        self.searcher = searcher
        self.recursion_resolver = recursion_resolver
        self.error_representor = error_representor

        self._current_request: Optional[Request] = None
        self.next_offset = 0
        self.recursion_stubs: Dict[Request, Any] = {}

    def provide(self, request: Request[T]) -> T:
        stub = self.recursion_resolver.process_recursion(request)
        if stub is not None:
            return stub

        self._current_request = request
        try:
            result = self._provide_non_recursive(request, 0)
        finally:
            self._current_request = None

        self.recursion_resolver.process_request_result(request, result)
        return result

    def provide_from_next(self) -> Any:
        if self._current_request is None:
            raise ValueError
        return self._provide_non_recursive(self._current_request, self.next_offset)

    def _provide_non_recursive(self, request: Request[T], search_offset: int) -> T:
        init_next_offset = self.next_offset
        exceptions = []
        for provide_callable, next_offset in self.searcher.search_candidates(
            search_offset, request
        ):
            self.next_offset = next_offset
            try:
                result = provide_callable(self, request)
            except CannotProvide as e:
                if e.is_terminal:
                    self.next_offset = init_next_offset
                    raise self._attach_request_context_note(e, request)
                exceptions.append(e)
                continue

            self.next_offset = init_next_offset
            return result

        raise self._attach_request_context_note(
            AggregateCannotProvide.make(
                self.error_representor.get_no_provider_description(request),
                exceptions,
                is_demonstrative=True,
            ),
            request,
        )

    def _attach_request_context_note(self, exc: E, request: Request) -> E:
        notes = self.error_representor.get_request_context_notes(request)
        for note in notes:
            add_note(exc, note)
        return exc


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
            element = self._combo[0][1]
            self._combo.clear()
            self._origins.clear()
            return [element]

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
