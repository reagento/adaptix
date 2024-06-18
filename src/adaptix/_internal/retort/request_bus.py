from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Iterable, List, Optional, Tuple, TypeVar

from ..provider.essential import (
    AggregateCannotProvide,
    CannotProvide,
    DirectMediator,
    Mediator,
    Request,
    RequestHandler,
)
from ..utils import add_note
from .builtin_mediator import RequestBus

RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT")


class ErrorRepresentor(ABC, Generic[RequestT]):
    @abstractmethod
    def get_no_provider_description(self, request: RequestT) -> str:
        ...

    @abstractmethod
    def get_request_context_notes(self, request: RequestT) -> Iterable[str]:
        ...


class RequestRouter(ABC, Generic[RequestT]):
    """An offset of each element must belong to [0; max_offset)"""

    @abstractmethod
    def route_handler(
        self,
        mediator: DirectMediator,
        request: RequestT,
        search_offset: int,
    ) -> Tuple[RequestHandler, int]:
        """
        :raises: StopIteration
        """

    @abstractmethod
    def get_max_offset(self) -> int:
        ...


E = TypeVar("E", bound=Exception)


class BasicRequestBus(RequestBus[RequestT, ResponseT], Generic[RequestT, ResponseT]):
    __slots__ = ("_router", "_error_representor", "_mediator_factory")

    def __init__(
        self,
        router: RequestRouter[RequestT],
        error_representor: ErrorRepresentor[RequestT],
        mediator_factory: Callable[[Request, int], Mediator],
    ):
        self._router = router
        self._error_representor = error_representor
        self._mediator_factory = mediator_factory

    def send(self, request: RequestT) -> Any:
        return self._send_inner(request, 0)

    def send_chaining(self, request: RequestT, search_offset: int) -> Any:
        return self._send_inner(request, search_offset)

    def _send_inner(self, request: RequestT, search_offset: int) -> Any:
        next_offset = search_offset
        exceptions: List[CannotProvide] = []
        while True:
            mediator = self._mediator_factory(request, search_offset)

            try:
                handler, next_offset = self._router.route_handler(mediator, request, next_offset)
            except StopIteration:
                raise self._attach_request_context_note(
                    AggregateCannotProvide.make(
                        self._error_representor.get_no_provider_description(request),
                        exceptions,
                        is_demonstrative=True,
                    ),
                    request,
                ) from None

            try:
                result = handler(mediator, request)
            except CannotProvide as e:
                if e.is_terminal:
                    raise self._attach_request_context_note(e, request)
                exceptions.append(e)
                continue

            return result

    def _attach_request_context_note(self, exc: E, request: RequestT) -> E:
        notes = self._error_representor.get_request_context_notes(request)
        for note in notes:
            add_note(exc, note)
        return exc


class RecursionResolver(ABC, Generic[RequestT, ResponseT]):
    @abstractmethod
    def track_recursion(self, request: RequestT) -> Optional[ResponseT]:
        ...

    @abstractmethod
    def track_response(self, request: RequestT, response: ResponseT) -> None:
        ...


class RecursiveRequestBus(BasicRequestBus[RequestT, ResponseT], Generic[RequestT, ResponseT]):
    __slots__ = (*BasicRequestBus.__slots__, "_recursion_resolver")

    def __init__(
        self,
        router: RequestRouter[RequestT],
        recursion_resolver: RecursionResolver[RequestT, ResponseT],
        error_representor: ErrorRepresentor[RequestT],
        mediator_factory: Callable[[Request, int], Mediator],
    ):
        super().__init__(router, error_representor, mediator_factory)
        self._recursion_resolver = recursion_resolver

    def send(self, request: RequestT) -> Any:
        stub = self._recursion_resolver.track_recursion(request)
        if stub is not None:
            return stub

        result = self._send_inner(request, 0)
        self._recursion_resolver.track_response(request, result)
        return result
