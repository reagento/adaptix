from typing import Generic, Sequence, Tuple, Type, TypeVar

from .essential import Provider, Request, RequestChecker, RequestHandler
from .request_checkers import AlwaysTrueRequestChecker

T = TypeVar("T")


class ValueProvider(Provider, Generic[T]):
    def __init__(self, request_cls: Type[Request[T]], value: T):
        self._request_cls = request_cls
        self._value = value

    def get_request_handlers(self) -> Sequence[Tuple[Type[Request], RequestChecker, RequestHandler]]:
        return [
            (self._request_cls, AlwaysTrueRequestChecker(), lambda m, r: self._value),
        ]

    def __repr__(self):
        return f"{type(self).__name__}({self._request_cls}, {self._value})"
