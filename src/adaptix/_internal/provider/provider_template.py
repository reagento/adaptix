from typing import Generic, Optional, Type, TypeVar

from .essential import CannotProvide, Mediator, Request
from .loc_stack_filtering import LocStackChecker, P, Pred, create_loc_stack_checker
from .provider_wrapper import ProviderWithLSC, RequestClassDeterminedProvider
from .static_provider import StaticProvider

T = TypeVar('T')


class ProviderWithAttachableLSC(StaticProvider, ProviderWithLSC):
    _loc_stack_checker: LocStackChecker = P.ANY

    def get_loc_stack_checker(self) -> Optional[LocStackChecker]:
        return self._loc_stack_checker


def for_predicate(pred: Pred):
    def decorator(cls: Type[ProviderWithAttachableLSC]):
        if not (isinstance(cls, type) and issubclass(cls, ProviderWithAttachableLSC)):
            raise TypeError(f"Only {ProviderWithAttachableLSC} child is allowed")

        # noinspection PyProtectedMember
        # pylint: disable=protected-access
        cls._loc_stack_checker = create_loc_stack_checker(pred)
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
