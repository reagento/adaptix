from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Union, Type, Callable, Tuple

from .request_cls import TypeRM, FieldNameRM
from .static_provider import StaticProvider, static_provision_action
from ..core import Provider, BaseFactory, CannotProvide, Request, SearchState, RequestDispatcher
from ..core.class_dispatcher import ClassDispatcherKeysView

T = TypeVar('T')


class RequestChecker(ABC):
    @abstractmethod
    def get_allowed_request_classes(self) -> Tuple[Type[Request], ...]:
        raise NotImplementedError

    @abstractmethod
    def _check_request(self, request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        raise NotImplementedError

    def __call__(self, request: Request) -> None:
        """Raise CannotProvide if the request does not meet the conditions"""
        allowed = self.get_allowed_request_classes()
        if isinstance(request, allowed):
            self._check_request(request)
        raise CannotProvide(f'Only instances of {allowed} are allowed')


@dataclass
class FieldNameRC(RequestChecker):
    field_name: str

    def get_allowed_request_classes(self) -> Tuple[Type[Request], ...]:
        return (FieldNameRM,)

    def _check_request(self, request: FieldNameRM) -> None:
        if self.field_name == request.field_name:
            return
        raise CannotProvide(f'field_name must be a {self.field_name!r}')


@dataclass
class SubclassRC(RequestChecker):
    type_: type

    def get_allowed_request_classes(self) -> Tuple[Type[Request], ...]:
        return (TypeRM,)

    def _check_request(self, request: TypeRM) -> None:
        if not isinstance(request.type, type):
            raise CannotProvide(f'{request.type} must be a class')

        if issubclass(request.type, self.type_):
            return
        raise CannotProvide(f'{request.type} must be a subclass of {self.type_}')


def create_builtin_req_checker(pred: Union[type, str]) -> RequestChecker:
    if isinstance(pred, str):
        return FieldNameRC(pred)
    if isinstance(pred, type):
        return SubclassRC(pred)
    raise TypeError(f'Expected {Union[type, str]}')


class NextProvider(StaticProvider):
    @static_provision_action(Request)
    def _np_proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request[T]) -> T:
        return factory.provide_with(s_state.start_from_next(), request)


class ConstrainingProxyProvider(Provider):
    def __init__(self, req_checker: RequestChecker, provider: Provider):
        self.req_checker = req_checker
        self.provider = provider

        req_checker_rdkw = ClassDispatcherKeysView(
            set(req_checker.get_allowed_request_classes())
        )

        self._rd = provider.get_request_dispatcher().keys().intersect(
            req_checker_rdkw
        ).bind('_cpp_proxy_provide')

        super().__init__()

    def get_request_dispatcher(self) -> RequestDispatcher:
        return self._rd

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
