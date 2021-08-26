from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Union

from .request_cls import TypeRequest, TypeFieldRequest
from ..core import Provider, BaseFactory, CannotProvide, provision_action, Request, SearchState

T = TypeVar('T')


class TypeRequestChecker(ABC):
    @abstractmethod
    def __call__(self, request: TypeRequest) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        raise NotImplementedError


class BuiltinTypeRequestChecker(TypeRequestChecker):
    ALLOWS = Union[type, str]

    # TODO: Add support for type hint as pred
    def __init__(self, pred: ALLOWS):
        if not isinstance(pred, (str, type)):
            raise TypeError(f'Expected {self.ALLOWS}')

        self.pred = pred

    def __call__(self, request: TypeRequest) -> None:
        if isinstance(self.pred, str):
            if isinstance(request, TypeFieldRequest) and self.pred == request.field_name:
                return

            raise CannotProvide

        if not isinstance(request.type, type):
            raise CannotProvide

        if issubclass(request.type, self.pred):
            return

        raise CannotProvide


class NextProvider(Provider):
    @provision_action(Request)
    def _np_proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request[T]) -> T:
        return factory.provide(s_state.start_from_next(), request)


@dataclass
class ConstrainingProxyProvider(Provider):
    tr_checker: TypeRequestChecker
    provider: Provider

    @provision_action(TypeRequest)
    def _cpp_proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: TypeRequest[T]) -> T:
        self.tr_checker(request)
        return self.provider.apply_provider(factory, s_state, request)
