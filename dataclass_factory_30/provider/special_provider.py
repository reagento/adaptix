from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from functools import partial
from typing import Literal, Optional

from dataclass_factory.exceptions import ParseError
from .basic_provider import ParserProvider, SerializerProvider, foreign_parser, for_type
from .essential import Mediator
from .request_cls import ParserRequest, SerializerRequest


def stub(arg):
    return arg


@for_type(datetime)
class DatetimeUnixTimeProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(datetime.fromtimestamp)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return stub


@for_type(datetime)
class DatetimeIsoFormatParserProvider(ParserProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(datetime.fromisoformat)


TimespecCases = Literal['auto', 'hours', 'minutes', 'seconds', 'milliseconds', 'microseconds']


@dataclass
@for_type(datetime)
class DatetimeIsoFormatSerializerProvider(SerializerProvider):
    sep: Optional[str] = None
    timespec: Optional[TimespecCases] = None

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        kwargs = {}
        if self.sep is not None:
            kwargs['sep'] = self.sep
        if self.timespec is not None:
            kwargs['timespec'] = self.timespec

        if kwargs:
            return partial(datetime.isoformat, **kwargs)
        return datetime.isoformat


@dataclass
@for_type(datetime)
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


@for_type(date)
class DateProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(date.fromisoformat)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return date.isoformat


@for_type(date)
class DateIsoFormatProvider(ParserProvider, SerializerProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(date.fromisoformat)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        return date.isoformat


@for_type(time)
class TimeIsoFormatParserProvider(ParserProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        return foreign_parser(time.fromisoformat)


@dataclass
@for_type(time)
class TimeIsoFormatSerializerProvider(SerializerProvider):
    timespec: Optional[TimespecCases] = None

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        if self.timespec is None:
            return foreign_parser(time.isoformat)
        return foreign_parser(partial(time.isoformat, self.timespec))


TimedeltaAttrs = Literal['weeks', 'days', 'hours', 'minutes', 'seconds', 'milliseconds', 'microseconds']


@dataclass
@for_type(timedelta)
class TimedeltaProvider(ParserProvider, SerializerProvider):
    attr: TimedeltaAttrs = 'seconds'

    def _provide_parser(self, mediator: Mediator, request: ParserRequest):
        attr = self.attr

        if attr == 'seconds':
            def timedelta_seconds_parser(value):
                return timedelta(seconds=value)

            return foreign_parser(timedelta_seconds_parser)

        def timedelta_parser(value):
            return timedelta(**{attr: value})

        return foreign_parser(timedelta_parser)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest):
        attr = self.attr

        if attr == 'seconds':
            def timedelta_seconds_serializer(value):
                return value.seconds

            return timedelta_seconds_serializer

        def timedelta_serializer(value):
            return getattr(value, attr)

        return timedelta_serializer


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
