from abc import ABC, abstractmethod
from functools import partial
from typing import Collection, Type, TypeVar, final

from ..common import Dumper, Loader, TypeHint
from ..load_error import TypeLoadError
from ..type_tools import create_union, normalize_type
from .essential import CannotProvide, Mediator, Provider, Request
from .request_cls import DumperRequest, LoaderRequest, get_type_from_request, replace_type
from .request_filtering import RequestChecker, match_origin
from .static_provider import StaticProvider, static_provision_action

T = TypeVar('T')


class ProviderWithRC(StaticProvider):
    def _check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        pass


def attach_request_checker(checker: RequestChecker, cls: Type[ProviderWithRC]):
    if not (isinstance(cls, type) and issubclass(cls, ProviderWithRC)):
        raise TypeError(f"Only {ProviderWithRC} child is allowed")

    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    if cls._check_request is not ProviderWithRC._check_request:
        raise RuntimeError("Can not attach request checker twice")

    cls._check_request = checker.check_request  # type: ignore
    return cls


def for_origin(tp: TypeHint):
    return partial(
        attach_request_checker,
        match_origin(tp)
    )


class LoaderProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action
    def _outer_provide_loader(self, mediator: Mediator, request: LoaderRequest):
        self._check_request(mediator, request)
        return self._provide_loader(mediator, request)

    @abstractmethod
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        ...


class DumperProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action
    def _outer_provide_dumper(self, mediator: Mediator, request: DumperRequest):
        self._check_request(mediator, request)
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

        if not request.strict_coercion:
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


class ABCProxy(Provider):
    def __init__(self, abstract: TypeHint, impl: TypeHint):
        self._abstract = normalize_type(abstract).origin
        self._impl = impl

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        if not isinstance(request, (LoaderRequest, DumperRequest)):
            raise CannotProvide

        norm = normalize_type(get_type_from_request(request))

        if norm.origin != self._abstract:
            raise CannotProvide

        return mediator.provide(replace_type(request, self._impl))
