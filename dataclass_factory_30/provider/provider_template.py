from abc import ABC, abstractmethod
from functools import partial
from typing import TypeVar, final, Type, Collection

from .definitions import TypeParseError
from .essential import Provider, Mediator, Request
from .provider_basics import RequestChecker, create_type_hint_req_checker
from .request_cls import ParserRequest, SerializerRequest
from .static_provider import StaticProvider, static_provision_action
from ..common import TypeHint, Parser, Serializer
from ..type_tools import create_union

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
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        pass


class SerializerProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action(SerializerRequest)
    def _outer_provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        self._check_request(request)
        return self._provide_serializer(mediator, request)

    @abstractmethod
    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        pass


class CoercionLimiter(ParserProvider):
    def __init__(self, parser_provider: Provider, allowed_strict_origins: Collection[type]):
        self.parser_provider = parser_provider

        if isinstance(allowed_strict_origins, list):
            allowed_strict_origins = tuple(allowed_strict_origins)

        self.allowed_strict_origins = allowed_strict_origins

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        parser = self.parser_provider.apply_provider(mediator, request)

        if not request.strict_coercion:
            return parser

        allowed_strict_origins = self.allowed_strict_origins

        if len(allowed_strict_origins) == 0:
            return parser

        if len(allowed_strict_origins) == 1:
            origin = next(iter(self.allowed_strict_origins))

            def strict_coercion_parser_1_origin(value):
                if type(value) == origin:
                    return parser(value)
                raise TypeParseError(origin)

            return strict_coercion_parser_1_origin

        union = create_union(tuple(allowed_strict_origins))

        def strict_coercion_parser(value):
            if type(value) in allowed_strict_origins:
                return parser(value)
            raise TypeParseError(union)

        return strict_coercion_parser

    def __repr__(self):
        return f"{type(self).__name__}({self.parser_provider}, {self.allowed_strict_origins})"
