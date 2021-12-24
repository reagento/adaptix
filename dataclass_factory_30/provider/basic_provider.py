from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Any, TypeVar, final, Type

from .definitions import PARSER_COMPAT_EXCEPTIONS, ParseError
from .essential import Mediator, Request
from .provider import RequestChecker, create_builtin_req_checker
from .request_cls import ParserRequest, SerializerRequest
from .static_provider import StaticProvider, static_provision_action
from ..common import Parser

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


def for_type(type_: Any):
    return partial(
        attach_request_checker,
        create_builtin_req_checker(type_)
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


def foreign_parser(func: Callable[[Any], T]) -> Parser[T]:
    def foreign_parser_wrapper(arg):
        try:
            return func(arg)
        except PARSER_COMPAT_EXCEPTIONS as e:
            raise ParseError() from e

    return foreign_parser_wrapper


class SerializerProvider(ProviderWithRC, ABC):
    @final
    @static_provision_action(SerializerRequest)
    def _outer_provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        self._check_request(request)
        return self._provide_serializer(mediator, request)

    @abstractmethod
    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        pass
