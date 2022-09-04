import re
from binascii import a2b_base64, b2a_base64
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Type, TypeVar, Union

from ..common import Parser, Serializer
from ..type_tools import normalize_type
from .definitions import ParseError, TypeParseError, ValueParseError
from .essential import Mediator, Request
from .provider_basics import ExactTypeRC, foreign_parser
from .provider_template import ParserProvider, ProviderWithRC, SerializerProvider, for_origin
from .request_cls import ParserRequest, SerializerRequest

T = TypeVar('T')


def stub(arg):
    return arg


@dataclass
class ForAnyDateTime(ProviderWithRC):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._request_checker = ExactTypeRC(normalize_type(self.cls))

    def _check_request(self, mediator: Mediator[T], request: Request[T]) -> None:
        self._request_checker.check_request(mediator, request)


@dataclass
class IsoFormatProvider(ForAnyDateTime, ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        return foreign_parser(self.cls.fromisoformat)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return self.cls.isoformat


@dataclass
@for_origin(datetime)
class DatetimeFormatProvider(ParserProvider, SerializerProvider):
    format: str

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        fmt = self.format

        def datetime_format_parser(value):
            return datetime.strptime(value, fmt)

        return foreign_parser(datetime_format_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        fmt = self.format

        def datetime_format_serializer(value: datetime):
            return value.strftime(fmt)

        return datetime_format_serializer


@for_origin(timedelta)
class TimedeltaProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def timedelta_parser(value):
            return timedelta(seconds=value)

        return foreign_parser(timedelta_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return timedelta.total_seconds


@for_origin(None)
class NoneProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def none_parser(data):
            if data is None:
                return None
            raise TypeParseError(None)

        return none_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return stub


class Base64SerializerMixin(SerializerProvider):
    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        def bytes_base64_serializer(data):
            return b2a_base64(data, newline=False).decode('ascii')

        return bytes_base64_serializer


B64_PATTERN = re.compile(b'[A-Za-z0-9+/]*={0,2}')


@for_origin(bytes)
class BytesBase64Provider(ParserProvider, Base64SerializerMixin):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def bytes_base64_parser(data):
            encoded = data.encode('ascii')
            if B64_PATTERN.fullmatch(encoded):
                return a2b_base64(encoded)
            raise ParseError

        return foreign_parser(bytes_base64_parser)


@for_origin(bytearray)
class BytearrayBase64Provider(ParserProvider, Base64SerializerMixin):
    _BYTES_PROVIDER = BytesBase64Provider()

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        bytes_parser = self._BYTES_PROVIDER.apply_provider(
            mediator, replace(request, type=bytes)
        )

        def bytearray_base64_parser(data):
            return bytearray(bytes_parser(data))

        return bytearray_base64_parser


def _regex_serializer(data: re.Pattern):
    return data.pattern


@for_origin(re.Pattern)
class RegexPatternProvider(ParserProvider, SerializerProvider):
    def __init__(self, flags: re.RegexFlag = re.RegexFlag(0)):
        self.flags = flags

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        flags = self.flags
        re_compile = re.compile

        def regex_parser(data):
            if not isinstance(data, str):
                raise TypeParseError(str)

            try:
                return re_compile(data, flags)
            except re.error as e:
                raise ValueParseError(str(e))

        return regex_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return _regex_serializer
