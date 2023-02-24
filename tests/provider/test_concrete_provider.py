import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from adaptix._internal.provider import (
    BytearrayBase64Provider,
    BytesBase64Provider,
    DatetimeFormatProvider,
    DumperRequest,
    IsoFormatProvider,
    LoaderRequest,
    NoneProvider,
    RegexPatternProvider,
    SecondsTimedeltaProvider,
    TypeHintLoc,
    ValueProvider,
)
from adaptix._internal.provider.request_cls import DebugPathRequest, LocMap, StrictCoercionRequest
from adaptix.load_error import DatetimeFormatMismatch, TypeLoadError, ValueLoadError
from tests_helpers import TestRetort, parametrize_bool, raises_path


def check_any_dt(loader):
    raises_path(
        TypeLoadError(str),
        lambda: loader(None)
    )
    raises_path(
        TypeLoadError(str),
        lambda: loader(10)
    )
    raises_path(
        TypeLoadError(str),
        lambda: loader(datetime(2011, 11, 4, 0, 0))
    )
    raises_path(
        TypeLoadError(str),
        lambda: loader(date(2019, 12, 4))
    )
    raises_path(
        TypeLoadError(str),
        lambda: loader(time(4, 23, 1))
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_datetime(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            IsoFormatProvider(datetime),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(datetime)
    assert loader('2011-11-04') == datetime(2011, 11, 4, 0, 0)
    assert loader('2011-11-04T00:05:23') == datetime(2011, 11, 4, 0, 5, 23)
    assert loader('2011-11-04T00:05:23+04:00') == datetime(
        2011, 11, 4, 0, 5, 23,
        tzinfo=timezone(timedelta(seconds=14400))
    )

    check_any_dt(loader)

    raises_path(
        ValueLoadError("Invalid isoformat string"),
        lambda: loader("some string")
    )

    dumper = retort.get_dumper(datetime)
    assert dumper(datetime(2011, 11, 4, 0, 0)) == '2011-11-04T00:00:00'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_date(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            IsoFormatProvider(date),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(date)
    assert loader('2019-12-04') == date(2019, 12, 4)
    check_any_dt(loader)

    raises_path(
        ValueLoadError("Invalid isoformat string"),
        lambda: loader("some string")
    )

    dumper = retort.get_dumper(date)
    assert dumper(date(2019, 12, 4)) == '2019-12-04'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_time(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            IsoFormatProvider(time),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(time)
    assert loader('04:23:01') == time(4, 23, 1)
    assert loader('04:23:01+04:00') == time(
        4, 23, 1,
        tzinfo=timezone(timedelta(seconds=14400))
    )
    check_any_dt(loader)

    raises_path(
        ValueLoadError("Invalid isoformat string"),
        lambda: loader("some string")
    )

    dumper = retort.get_dumper(time)
    assert dumper(time(4, 23, 1)) == '04:23:01'


@parametrize_bool('strict_coercion', 'debug_path')
def test_datetime_format_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            DatetimeFormatProvider("%Y-%m-%d"),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(datetime)
    assert loader("3045-02-13") == datetime(year=3045, month=2, day=13)

    check_any_dt(loader)

    raises_path(
        DatetimeFormatMismatch("%Y-%m-%d"),
        lambda: loader("some string")
    )

    dumper = retort.get_dumper(datetime)
    assert dumper(datetime(year=3045, month=2, day=13)) == "3045-02-13"


@parametrize_bool('strict_coercion', 'debug_path')
def test_seconds_timedelta_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            SecondsTimedeltaProvider(),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(timedelta)
    assert loader(10) == timedelta(seconds=10)
    assert loader(600) == timedelta(minutes=10)
    assert loader(0.123) == timedelta(milliseconds=123)
    assert loader(Decimal('0.123')) == timedelta(milliseconds=123)

    dumper = retort.get_dumper(timedelta)
    assert dumper(timedelta(minutes=10)) == 600


@parametrize_bool('strict_coercion', 'debug_path')
def test_none_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            NoneProvider(),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(None)

    assert loader(None) is None

    raises_path(
        TypeLoadError(None),
        lambda: loader(10)
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytes_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            BytesBase64Provider(),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(bytes)

    assert loader('YWJjZA==') == b'abcd'

    raises_path(
        ValueLoadError('Bad base64 string'),
        lambda: loader('Hello, world'),
    )

    raises_path(
        ValueLoadError(
            'Invalid base64-encoded string: number of data characters (5)'
            ' cannot be 1 more than a multiple of 4'
        ),
        lambda: loader('aaaaa='),
    )

    raises_path(
        ValueLoadError('Incorrect padding'),
        lambda: loader('YWJjZA'),
    )

    raises_path(
        TypeLoadError(str),
        lambda: loader(108),
    )

    dumper = retort.get_dumper(bytes)
    assert dumper(b'abcd') == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytearray_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            BytearrayBase64Provider(),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(bytearray)

    assert loader('YWJjZA==') == bytearray(b'abcd')

    raises_path(
        ValueLoadError('Bad base64 string'),
        lambda: loader('Hello, world'),
    )

    raises_path(
        ValueLoadError(
            'Invalid base64-encoded string: number of data characters (5)'
            ' cannot be 1 more than a multiple of 4'
        ),
        lambda: loader('aaaaa='),
    )

    raises_path(
        ValueLoadError('Incorrect padding'),
        lambda: loader('YWJjZA'),
    )

    raises_path(
        TypeLoadError(str),
        lambda: loader(108),
    )

    dumper = retort.get_dumper(bytearray)
    assert dumper(bytearray(b'abcd')) == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_regex_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            RegexPatternProvider(),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    loader = retort.get_loader(re.Pattern)

    assert loader(r'\w') == re.compile(r'\w')

    raises_path(
        TypeLoadError(str),
        lambda: loader(10)
    )
    raises_path(
        ValueLoadError("bad escape (end of pattern) at position 0"),
        lambda: loader('\\')
    )

    dumper = retort.get_dumper(re.Pattern)
    assert dumper(re.compile(r'\w')) == r'\w'
