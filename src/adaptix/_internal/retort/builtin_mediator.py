from abc import ABC, abstractmethod
from typing import Generic, Mapping, Type, TypeVar

from ..provider.essential import CannotProvide, Mediator, Request

T = TypeVar("T")


RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT")


class RequestBus(ABC, Generic[RequestT, ResponseT]):
    @abstractmethod
    def send(self, request: RequestT) -> ResponseT:
        pass

    @abstractmethod
    def send_chaining(self, request: RequestT, search_offset: int) -> ResponseT:
        pass


class BuiltinMediator(Mediator[ResponseT], Generic[ResponseT]):
    __slots__ = ("_request_buses", "_request", "_search_offset")

    def __init__(self, request_buses: Mapping[Type[Request], RequestBus], request: Request, search_offset: int):
        self._request_buses = request_buses
        self._request = request
        self._search_offset = search_offset

    def provide(self, request: Request[T]) -> T:
        try:
            request_bus = self._request_buses[type(request)]
        except KeyError:
            # TODO: add description
            raise CannotProvide() from None

        return request_bus.send(request)

    def provide_from_next(self) -> ResponseT:
        return self._request_buses[type(self._request)].send_chaining(self._request, self._search_offset)
