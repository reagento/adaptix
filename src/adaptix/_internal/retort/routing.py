from abc import ABC, abstractmethod
from itertools import islice
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple, Type, TypeVar

from ..common import TypeHint
from ..provider.essential import CannotProvide, Mediator, Provider, Request
from ..provider.loc_stack_filtering import ExactOriginLSC
from ..provider.provider_wrapper import ProviderWithLSC, RequestClassDeterminedProvider
from ..provider.request_cls import LocatedRequest, TypeHintLoc, try_normalize_type

T = TypeVar('T')
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
        self._combo: List[Tuple[ExactOriginLSC, Provider]] = []
        self._origins: Set[TypeHint] = set()

    def add_element(self, provider: Provider) -> bool:
        if not isinstance(provider, ProviderWithLSC):
            return False
        loc_stack_checker = provider.get_loc_stack_checker()
        if not isinstance(loc_stack_checker, ExactOriginLSC):
            return False
        if loc_stack_checker.origin in self._origins:
            return False

        self._combo.append((loc_stack_checker, provider))
        self._origins.add(loc_stack_checker.origin)
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


class ExactOriginMergedProvider(Provider):
    def __init__(self, origins_to_providers: Sequence[Tuple[ExactOriginLSC, Provider]]):
        self.origin_to_provider = {
            loc_stack_checker.origin: provider
            for loc_stack_checker, provider in reversed(origins_to_providers)
        }

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide(f'Request must be instance of {LocatedRequest}')

        loc = request.last_map.get_or_raise(
            TypeHintLoc,
            lambda: CannotProvide(f'Request location must be instance of {TypeHintLoc}')
        )
        norm = try_normalize_type(loc.type)
        try:
            provider = self.origin_to_provider[norm.origin]
        except KeyError:
            raise CannotProvide from None

        return provider.apply_provider(mediator, request)


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
