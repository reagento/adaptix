from abc import ABC, abstractmethod
from functools import partial
from typing import Collection, Optional, Type, TypeVar, final

from ..common import Dumper, Loader, TypeHint
from ..load_error import TypeLoadError
from ..type_tools import create_union, normalize_type
from .essential import Mediator, Provider
from .request_cls import DumperRequest, LoaderRequest, LocMap, StrictCoercionRequest, TypeHintLoc
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


class CoercionLimiter(LoaderProvider):
    def __init__(self, loader_provider: Provider, allowed_strict_origins: Collection[type]):
        self.loader_provider = loader_provider

        if isinstance(allowed_strict_origins, list):
            allowed_strict_origins = tuple(allowed_strict_origins)

        self.allowed_strict_origins = allowed_strict_origins

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        loader = self.loader_provider.apply_provider(mediator, request)
        strict_coercion = mediator.provide(StrictCoercionRequest(loc_map=request.loc_map))
        if not strict_coercion:
            return loader

        allowed_strict_origins = self.allowed_strict_origins

        if len(allowed_strict_origins) == 0:
            return loader

        if len(allowed_strict_origins) == 1:
            origin = next(iter(self.allowed_strict_origins))

            def strict_coercion_loader_1_origin(value):
                if type(value) == origin:  # pylint: disable=unidiomatic-typecheck
                    return loader(value)
                raise TypeLoadError(origin)

            return strict_coercion_loader_1_origin

        union = create_union(tuple(allowed_strict_origins))

        def strict_coercion_loader(value):
            if type(value) in allowed_strict_origins:
                return loader(value)
            raise TypeLoadError(union)

        return strict_coercion_loader

    def __repr__(self):
        return f"{type(self).__name__}({self.loader_provider}, {self.allowed_strict_origins})"

    def get_request_checker(self) -> Optional[RequestChecker]:
        if isinstance(self.loader_provider, ProviderWithRC):
            return self.loader_provider.get_request_checker()
        return None


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
