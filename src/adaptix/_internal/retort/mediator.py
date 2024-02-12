from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Iterable, Optional, TypeVar

from ..provider.essential import AggregateCannotProvide, CannotProvide, Mediator, Request
from ..utils import add_note
from .routing import RecipeSearcher

T = TypeVar('T')


class RecursionResolver(ABC, Generic[T]):
    @abstractmethod
    def track_recursion(self, request: Request[T]) -> Optional[Any]:
        ...

    @abstractmethod
    def process_request_result(self, request: Request[T], result: T) -> None:
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
        stub = self.recursion_resolver.track_recursion(request)
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
