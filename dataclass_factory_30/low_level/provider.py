from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Union, Type, Callable

from .request_cls import TypeRM, FieldNameRM
from ..core import Provider, BaseFactory, CannotProvide, provision_action, Request, SearchState

T = TypeVar('T')


class RequestChecker(ABC):
    @abstractmethod
    def __call__(self, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        raise NotImplementedError


@dataclass
class FieldNameRC(RequestChecker):
    field_name: str

    def __call__(self, request: Request) -> None:
        if isinstance(request, FieldNameRM):
            if self.field_name == request.field_name:
                return
            raise CannotProvide(f'field_name must be a {self.field_name!r}')

        raise CannotProvide(f'Only {FieldNameRM} instance is allowed')


@dataclass
class SubclassRC(RequestChecker):
    type_: type

    def __call__(self, request: Request) -> None:
        if isinstance(request, TypeRM):
            if not isinstance(request.type, type):
                raise CannotProvide(f'{request.type} must be a class')

            if issubclass(request.type, self.type_):
                return
            raise CannotProvide(f'{request.type} must be a subclass of {self.type_}')

        raise CannotProvide(f'Only {TypeRM} instance is allowed')


def create_builtin_req_checker(pred: Union[type, str]) -> RequestChecker:
    if isinstance(pred, str):
        return FieldNameRC(pred)
    if isinstance(pred, type):
        return SubclassRC(pred)
    raise TypeError(f'Expected {Union[type, str]}')


class NextProvider(Provider):
    @provision_action(Request)
    def _np_proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request[T]) -> T:
        return factory.provide(s_state.start_from_next(), request)


@dataclass
class ConstrainingProxyProvider(Provider):
    req_checker: RequestChecker
    provider: Provider

    @provision_action(Request)
    def _cpp_proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request[T]) -> T:
        self.req_checker(request)
        return self.provider.apply_provider(factory, s_state, request)


@dataclass
class FuncProvider(Provider):
    request_cls: Type[Request]
    func: Callable


@dataclass
class ConstructorParserProvider(Provider):
    func: Callable
