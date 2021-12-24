from abc import ABC, abstractmethod
from functools import partial
from typing import TypeVar, final, Type

from .essential import Mediator, Request
from .provider_basics import RequestChecker, create_type_hint_req_checker
from .request_cls import ParserRequest, SerializerRequest
from .static_provider import StaticProvider, static_provision_action
from ..common import TypeHint

T = TypeVar('T')


class ProviderWithRC(StaticProvider):
    def _check_request(self, request: Request) -> None:
        pass


def attach_request_checker(checker: RequestChecker, cls: Type[ProviderWithRC]):
    if not (isinstance(cls, type) and issubclass(cls, ProviderWithRC)):
        raise TypeError(f"Only {ProviderWithRC} child is allowed")

    # noinspection PyProtectedMember
    if cls._check_request is not ProviderWithRC._check_request:
        raise RuntimeError("Can not attach request checker twice")

    cls._check_request = checker  # type: ignore
    return cls


def for_type(tp: TypeHint):
    return partial(
        attach_request_checker,
        create_type_hint_req_checker(tp)
    )


class ParserProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action(ParserRequest)
    def _outer_provide_parser(self, mediator: Mediator, request: ParserRequest):
        self._check_request(request)
        return self._provide_parser(mediator, request)

    @abstractmethod
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        pass


class SerializerProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action(SerializerRequest)
    def _outer_provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        self._check_request(request)
        return self._provide_serializer(mediator, request)

    @abstractmethod
    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        pass
