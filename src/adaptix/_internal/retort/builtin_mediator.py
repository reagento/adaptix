from abc import ABC, abstractmethod
from typing import Callable, Generic, Mapping, Type, TypeVar

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
    __slots__ = ("_request_buses", "_request", "_search_offset", "_no_request_bus_error_maker")

    def __init__(
        self,
        request_buses: Mapping[Type[Request], RequestBus],
        request: Request,
        search_offset: int,
        no_request_bus_error_maker: Callable[[Request], CannotProvide],
    ):
        self._request_buses = request_buses
        self._request = request
        self._search_offset = search_offset
        self._no_request_bus_error_maker = no_request_bus_error_maker

    def provide(self, request: Request[T]) -> T:
        try:
            request_bus = self._request_buses[type(request)]
        except KeyError:
            raise self._no_request_bus_error_maker(request) from None

        return request_bus.send(request)

    def provide_from_next(self) -> ResponseT:
        return self._request_buses[type(self._request)].send_chaining(self._request, self._search_offset)
