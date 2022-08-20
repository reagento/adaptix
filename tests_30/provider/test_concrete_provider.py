import re
from datetime import date, datetime, time, timedelta, timezone

from dataclass_factory_30.provider import (
    BytearrayBase64Provider,
    BytesBase64Provider,
    DatetimeFormatProvider,
    IsoFormatProvider,
    NoneProvider,
    ParseError,
    ParserRequest,
    RegexPatternProvider,
    SerializerRequest,
    TimedeltaProvider,
)
from dataclass_factory_30.provider.definitions import TypeParseError, ValueParseError
from tests_helpers import TestFactory, parametrize_bool, raises_path


def check_any_dt(parser):
    raises_path(
        ParseError(),
        lambda: parser(None)
    )
    raises_path(
        ParseError(),
        lambda: parser(10)
    )
    raises_path(
        ParseError(),
        lambda: parser("some string")
    )
    raises_path(
        ParseError(),
        lambda: parser(datetime(2011, 11, 4, 0, 0))
    )
    raises_path(
        ParseError(),
        lambda: parser(date(2019, 12, 4))
    )
    raises_path(
        ParseError(),
        lambda: parser(time(4, 23, 1))
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_datetime(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[IsoFormatProvider(datetime)]
    )

    parser = factory.provide(
        ParserRequest(
            type=datetime,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('2011-11-04') == datetime(2011, 11, 4, 0, 0)
    assert parser('2011-11-04T00:05:23') == datetime(2011, 11, 4, 0, 5, 23)
    assert parser('2011-11-04T00:05:23+04:00') == datetime(
        2011, 11, 4, 0, 5, 23,
        tzinfo=timezone(timedelta(seconds=14400))
    )

    check_any_dt(parser)

    serializer = factory.provide(
        SerializerRequest(type=datetime, debug_path=debug_path)
    )

    assert serializer(datetime(2011, 11, 4, 0, 0)) == '2011-11-04T00:00:00'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_date(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[IsoFormatProvider(date)]
    )

    parser = factory.provide(
        ParserRequest(
            type=date,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('2019-12-04') == date(2019, 12, 4)
    check_any_dt(parser)

    serializer = factory.provide(
        SerializerRequest(type=date, debug_path=debug_path)
    )

    assert serializer(date(2019, 12, 4)) == '2019-12-04'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_time(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[IsoFormatProvider(time)]
    )

    parser = factory.provide(
        ParserRequest(
            type=time,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('04:23:01') == time(4, 23, 1)
    assert parser('04:23:01+04:00') == time(
        4, 23, 1,
        tzinfo=timezone(timedelta(seconds=14400))
    )
    check_any_dt(parser)

    serializer = factory.provide(
        SerializerRequest(type=time, debug_path=debug_path)
    )

    assert serializer(time(4, 23, 1)) == '04:23:01'


@parametrize_bool('strict_coercion', 'debug_path')
def test_datetime_format_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[DatetimeFormatProvider("%Y-%m-%d")]
    )

    parser = factory.provide(
        ParserRequest(
            type=datetime,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser("3045-02-13") == datetime(year=3045, month=2, day=13)

    check_any_dt(parser)

    serializer = factory.provide(
        SerializerRequest(type=datetime, debug_path=debug_path)
    )

    assert serializer(datetime(year=3045, month=2, day=13)) == "3045-02-13"


@parametrize_bool('strict_coercion', 'debug_path')
def test_timedelta_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[TimedeltaProvider()]
    )

    parser = factory.provide(
        ParserRequest(
            type=timedelta,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser(10) == timedelta(seconds=10)
    assert parser(600) == timedelta(minutes=10)

    serializer = factory.provide(
        SerializerRequest(type=timedelta, debug_path=debug_path)
    )

    assert serializer(timedelta(minutes=10)) == 600


@parametrize_bool('strict_coercion', 'debug_path')
def test_none_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[NoneProvider()]
    )

    parser = factory.provide(
        ParserRequest(
            type=None,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser(None) is None

    raises_path(
        ParseError(),
        lambda: parser(10)
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytes_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[BytesBase64Provider()]
    )

    parser = factory.provide(
        ParserRequest(
            type=bytes,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('YWJjZA==') == b'abcd'

    raises_path(
        ParseError(),
        lambda: parser('YWJjZA')
    )

    serializer = factory.provide(
        SerializerRequest(type=bytes, debug_path=debug_path)
    )

    assert serializer(b'abcd') == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytearray_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[BytearrayBase64Provider()]
    )

    parser = factory.provide(
        ParserRequest(
            type=bytearray,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser('YWJjZA==') == bytearray(b'abcd')

    raises_path(
        ParseError(),
        lambda: parser('YWJjZA')
    )

    serializer = factory.provide(
        SerializerRequest(type=bytearray, debug_path=debug_path)
    )

    assert serializer(bytearray(b'abcd')) == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_regex_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[RegexPatternProvider()]
    )

    parser = factory.provide(
        ParserRequest(
            type=re.Pattern,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser(r'\w') == re.compile(r'\w')

    raises_path(
        TypeParseError(str),
        lambda: parser(10)
    )
    raises_path(
        ValueParseError("bad escape (end of pattern) at position 0"),
        lambda: parser('\\')
    )

    serializer = factory.provide(
        SerializerRequest(type=re.Pattern, debug_path=debug_path)
    )

    assert serializer(re.compile(r'\w')) == r'\w'
