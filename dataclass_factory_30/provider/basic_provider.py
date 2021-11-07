from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Any, TypeVar, final, Type, ClassVar

from .definitions import PARSER_COMPAT_EXCEPTIONS, ParseError
from .essential import Mediator, CannotProvide
from .request_cls import ParserRequest, SerializerRequest
from .static_provider import StaticProvider, static_provision_action
from ..common import Parser, TypeHint
from ..type_tools import normalize_type

T = TypeVar('T')


def _dummy_validator(x):
    return


TypeValidator = Callable[[TypeHint], None]


class ProviderWithTypeValidator(StaticProvider):
    _type_validator: ClassVar[TypeValidator] = staticmethod(_dummy_validator)


def attach_validator(validator: TypeValidator, cls: Type[ProviderWithTypeValidator]):
    if not (isinstance(cls, type) and issubclass(cls, ProviderWithTypeValidator)):
        raise TypeError(f"Only {ProviderWithTypeValidator} child is allowed")

    if cls._type_validator.__func__ is not _dummy_validator:  # type: ignore
        raise RuntimeError(f"Can not attach validator twice")

    cls._type_validator = validator


def for_class(cls: type):
    def for_class_validator(x: TypeHint):
        if x != cls:
            raise CannotProvide

    return partial(attach_validator, for_class_validator)


def for_origin(origin: Any):
    def for_origin_validator(x: TypeHint):
        norm = normalize_type(x)
        if norm.origin != origin:
            raise CannotProvide

    return partial(attach_validator, for_origin_validator)


class ParserProvider(ProviderWithTypeValidator, ABC):
    @final
    @static_provision_action(ParserRequest)
    def _real_provide_parser(self, mediator: Mediator, request: ParserRequest):
        self._type_validator(request.type)
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


class SerializerProvider(ProviderWithTypeValidator, ABC):
    @final
    @static_provision_action(SerializerRequest)
    def _real_provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        self._type_validator(request.type)
        return self._provide_serializer(mediator, request)

    @abstractmethod
    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        pass
