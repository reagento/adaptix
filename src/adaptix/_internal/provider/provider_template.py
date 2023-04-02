from abc import ABC, abstractmethod
from functools import partial
from typing import Optional, Type, TypeVar, final

from ..common import Dumper, Loader, TypeHint
from ..type_tools import normalize_type
from .essential import Mediator
from .request_cls import DumperRequest, LoaderRequest, LocMap, TypeHintLoc
from .request_filtering import AnyRequestChecker, ExactOriginRC, ProviderWithRC, RequestChecker, match_origin
from .static_provider import StaticProvider, static_provision_action

T = TypeVar('T')


class ProviderWithAttachableRC(StaticProvider, ProviderWithRC):
    _request_checker: RequestChecker = AnyRequestChecker()

    def get_request_checker(self) -> Optional[RequestChecker]:
        return self._request_checker


def attach_request_checker(checker: RequestChecker, cls: Type[ProviderWithAttachableRC]):
    if not (isinstance(cls, type) and issubclass(cls, ProviderWithAttachableRC)):
        raise TypeError(f"Only {ProviderWithAttachableRC} child is allowed")

    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    cls._request_checker = checker
    return cls


def for_origin(tp: TypeHint):
    return partial(
        attach_request_checker,
        match_origin(tp)
    )


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
    def __init__(self, abstract: TypeHint, impl: TypeHint):
        self._abstract = normalize_type(abstract).origin
        self._impl = impl
        self._request_checker = ExactOriginRC(self._abstract)

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        return mediator.provide(
            LoaderRequest(
                loc_map=LocMap(TypeHintLoc(type=self._impl))
            )
        )

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        return mediator.provide(
            DumperRequest(
                loc_map=LocMap(TypeHintLoc(type=self._impl))
            )
        )
