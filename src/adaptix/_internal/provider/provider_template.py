from abc import ABC, abstractmethod
from typing import Generic, Optional, Type, TypeVar, final

from ..common import Dumper, Loader, TypeHint
from ..essential import CannotProvide, Mediator, Request
from ..type_tools import normalize_type
from .provider_wrapper import RequestClassDeterminedProvider
from .request_cls import DumperRequest, LoaderRequest, LocMap, TypeHintLoc
from .request_filtering import (
    AnyRequestChecker,
    ExactOriginRC,
    Pred,
    ProviderWithRC,
    RequestChecker,
    create_request_checker,
)
from .static_provider import StaticProvider, static_provision_action

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


class LoaderProvider(ProviderWithAttachableRC, ABC):
    @final
    @static_provision_action
    def _outer_provide_loader(self, mediator: Mediator, request: LoaderRequest):
        self._request_checker.check_request(mediator, request)
        return self._provide_loader(mediator, request)

    @abstractmethod
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        ...


class DumperProvider(ProviderWithAttachableRC, ABC):
    @final
    @static_provision_action
    def _outer_provide_dumper(self, mediator: Mediator, request: DumperRequest):
        self._request_checker.check_request(mediator, request)
        return self._provide_dumper(mediator, request)

    @abstractmethod
    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        ...


class ABCProxy(LoaderProvider, DumperProvider):
    def __init__(self, abstract: TypeHint, impl: TypeHint, for_loader: bool = True, for_dumper: bool = True):
        self._abstract = normalize_type(abstract).origin
        self._impl = impl
        self._request_checker = ExactOriginRC(self._abstract)
        self._for_loader = for_loader
        self._for_dumper = for_dumper

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        if not self._for_loader:
            raise CannotProvide

        return mediator.mandatory_provide(
            LoaderRequest(
                loc_map=LocMap(TypeHintLoc(type=self._impl))
            ),
            lambda x: f'Cannot create loader for union. Loader for {self._impl} cannot be created',
        )

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        if not self._for_dumper:
            raise CannotProvide

        return mediator.mandatory_provide(
            DumperRequest(
                loc_map=LocMap(TypeHintLoc(type=self._impl))
            ),
            lambda x: f'Cannot create dumper for union. Dumper for {self._impl} cannot be created',
        )


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
