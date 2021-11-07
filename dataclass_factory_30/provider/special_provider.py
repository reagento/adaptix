from dataclasses import dataclass
from datetime import datetime, date
from functools import partial
from typing import Literal, Optional

from dataclass_factory.exceptions import ParseError
from . import Mediator, ParserRequest, SerializerRequest
from .basic_provider import ParserProvider, SerializerProvider, foreign_parser, for_class, for_origin


def stub(arg):
    return arg


@for_class(datetime)
class DatetimeUnixTimeProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(datetime.fromtimestamp)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return stub


@for_class(datetime)
class DatetimeIsoFormatParserProvider(ParserProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(datetime.fromisoformat)


TIMESPEC_VARIANTS = Literal['auto', 'hours', 'minutes', 'seconds', 'milliseconds', 'microseconds']


@dataclass
@for_class(datetime)
class DatetimeIsoFormatSerializerProvider(SerializerProvider):
    sep: Optional[str] = None
    timespec: Optional[TIMESPEC_VARIANTS] = None

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        kwargs = {}
        if self.sep is not None:
            kwargs['sep'] = self.sep
        if self.timespec is not None:
            kwargs['timespec'] = self.timespec

        if kwargs:
            return foreign_parser(partial(datetime.isoformat, **kwargs))
        return foreign_parser(datetime.isoformat)


@dataclass
@for_class(datetime)
class DatetimeFormattedProvider(ParserProvider, SerializerProvider):
    format: str

    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        fmt = self.format

        def datetime_formatted_parser(value):
            return datetime.strptime(value, fmt)

        return foreign_parser(datetime_formatted_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        def datetime_formatted_serializer(value: datetime):
            return value.strftime(self.format)

        return datetime_formatted_serializer


@for_origin(None)
class NoneProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        def none_parser(data):
            if data is None:
                return None
            raise ParseError

        return none_parser

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return stub

