import re
from binascii import a2b_base64, b2a_base64
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Union, Type

from .definitions import ParseError
from .essential import Mediator
from .provider_basics import ExactTypeRC, foreign_parser
from .provider_template import ParserProvider, SerializerProvider, for_type, ProviderWithRC
from .request_cls import ParserRequest, SerializerRequest
from ..common import Parser, Serializer
from ..type_tools import normalize_type


def stub(arg):
    return arg


@dataclass
class ForAnyDateTime(ProviderWithRC):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._check_request = ExactTypeRC(normalize_type(self.cls))


@dataclass
class IsoFormatProvider(ForAnyDateTime, ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        return foreign_parser(self.cls.fromisoformat)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return self.cls.isoformat


@dataclass
@for_type(datetime)
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


@for_type(timedelta)
class TimedeltaProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def timedelta_parser(value):
            return timedelta(seconds=value)

        return foreign_parser(timedelta_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return timedelta.total_seconds


@for_type(None)
class NoneProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def none_parser(data):
            if data is None:
                return None
            raise ParseError

        return none_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        return stub


B64_PATTERN = re.compile(b'[A-Za-z0-9+/]*={0,2}')


@for_type(bytes)
class BytesBase64Provider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        def bytes_base64_parser(data):
            encoded = data.encode('ascii')
            if B64_PATTERN.fullmatch(encoded):
                return a2b_base64(encoded)
            raise ParseError

        return foreign_parser(bytes_base64_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        def bytes_base64_serializer(data):
            return b2a_base64(data, newline=False).decode('ascii')

        return bytes_base64_serializer
