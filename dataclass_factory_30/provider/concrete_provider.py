from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Union, Type

from .definitions import ParseError
from .essential import Mediator
from .provider_basics import ExactTypeRC, foreign_parser
from .provider_template import ParserProvider, SerializerProvider, for_type, ProviderWithRC
from .request_cls import ParserRequest, SerializerRequest


def stub(arg):
    return arg


@dataclass
class ForAnyDateTime(ProviderWithRC):
    cls: Type[Union[date, time]]

    def __post_init__(self):
        self._check_request = ExactTypeRC(self.cls)


@dataclass
class IsoFormatProvider(ForAnyDateTime, ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(self.cls.fromisoformat)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return self.cls.isoformat


@dataclass
class AnyDateTimeFormatProvider(ForAnyDateTime, ParserProvider, SerializerProvider):
    format: str

    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        fmt = self.format

        def any_date_time_format_parser(value):
            return datetime.strptime(value, fmt)

        return foreign_parser(any_date_time_format_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        fmt = self.format

        def any_date_time_format_serializer(value: datetime):
            return value.strftime(fmt)

        return any_date_time_format_serializer


def datetime_format_provider(fmt: str):
    return AnyDateTimeFormatProvider(datetime, fmt)


def date_format_provider(fmt: str):
    return AnyDateTimeFormatProvider(date, fmt)


def time_format_provider(fmt: str):
    return AnyDateTimeFormatProvider(time, fmt)


@for_type(timedelta)
class TimedeltaProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        def timedelta_parser(value):
            return timedelta(seconds=value)

        return foreign_parser(timedelta_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return timedelta.total_seconds


@for_type(None)
class NoneProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        def none_parser(data):
            if data is None:
                return None
            raise ParseError

        return none_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return stub
