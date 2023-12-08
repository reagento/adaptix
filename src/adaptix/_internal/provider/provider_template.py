from typing import Generic, Optional, Type, TypeVar

from .essential import CannotProvide, Mediator, Request
from .provider_wrapper import RequestClassDeterminedProvider
from .request_filtering import AnyRequestChecker, Pred, ProviderWithRC, RequestChecker, create_request_checker
from .static_provider import StaticProvider

T = TypeVar('T')


class ProviderWithAttachableRC(StaticProvider, ProviderWithRC):
    _request_checker: RequestChecker = AnyRequestChecker()

    def get_request_checker(self) -> Optional[RequestChecker]:
        return self._request_checker


def for_predicate(pred: Pred):
    def decorator(cls: Type[ProviderWithAttachableRC]):
        if not (isinstance(cls, type) and issubclass(cls, ProviderWithAttachableRC)):
            raise TypeError(f"Only {ProviderWithAttachableRC} child is allowed")

        # noinspection PyProtectedMember
        # pylint: disable=protected-access
        cls._request_checker = create_request_checker(pred)
        return cls

    return decorator


class ValueProvider(RequestClassDeterminedProvider, Generic[T]):
    def __init__(self, request_cls: Type[Request[T]], value: T):
        self._request_cls = request_cls
        self._value = value

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._request_cls):
            raise CannotProvide

        return self._value

    def __repr__(self):
        return f"{type(self).__name__}({self._request_cls}, {self._value})"

    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        return issubclass(request_cls, self._request_cls)
