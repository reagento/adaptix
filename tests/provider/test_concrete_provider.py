import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from dataclass_factory.provider import (
    BytearrayBase64Provider,
    BytesBase64Provider,
    DatetimeFormatProvider,
    DumperRequest,
    IsoFormatProvider,
    LoaderRequest,
    NoneProvider,
    RegexPatternProvider,
    SecondsTimedeltaProvider,
    TypeHintLocation,
)
from dataclass_factory.provider.concrete_provider import DatetimeFormatMismatch
from dataclass_factory.provider.exceptions import TypeLoadError, ValueLoadError
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
        recipe=[IsoFormatProvider(datetime)]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=datetime),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=datetime),
            debug_path=debug_path,
        )
    )

    assert dumper(datetime(2011, 11, 4, 0, 0)) == '2011-11-04T00:00:00'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_date(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[IsoFormatProvider(date)]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=date),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader('2019-12-04') == date(2019, 12, 4)
    check_any_dt(loader)

    raises_path(
        ValueLoadError("Invalid isoformat string"),
        lambda: loader("some string")
    )

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=date),
            debug_path=debug_path,
        )
    )

    assert dumper(date(2019, 12, 4)) == '2019-12-04'


@parametrize_bool('strict_coercion', 'debug_path')
def test_iso_format_provider_time(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[IsoFormatProvider(time)]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=time),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=time),
            debug_path=debug_path,
        )
    )

    assert dumper(time(4, 23, 1)) == '04:23:01'


@parametrize_bool('strict_coercion', 'debug_path')
def test_datetime_format_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[DatetimeFormatProvider("%Y-%m-%d")]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=datetime),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader("3045-02-13") == datetime(year=3045, month=2, day=13)

    check_any_dt(loader)

    raises_path(
        DatetimeFormatMismatch("%Y-%m-%d"),
        lambda: loader("some string")
    )

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=datetime),
            debug_path=debug_path,
        )
    )

    assert dumper(datetime(year=3045, month=2, day=13)) == "3045-02-13"


@parametrize_bool('strict_coercion', 'debug_path')
def test_seconds_timedelta_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[SecondsTimedeltaProvider()]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=timedelta),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader(10) == timedelta(seconds=10)
    assert loader(600) == timedelta(minutes=10)
    assert loader(0.123) == timedelta(milliseconds=123)
    assert loader(Decimal('0.123')) == timedelta(milliseconds=123)

    dumper = retort.provide(
        DumperRequest(loc=TypeHintLocation(type=timedelta), debug_path=debug_path)
    )

    assert dumper(timedelta(minutes=10)) == 600


@parametrize_bool('strict_coercion', 'debug_path')
def test_none_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[NoneProvider()]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=None),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader(None) is None

    raises_path(
        TypeLoadError(None),
        lambda: loader(10)
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytes_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[BytesBase64Provider()]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=bytes),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=bytes),
            debug_path=debug_path,
        )
    )

    assert dumper(b'abcd') == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_bytearray_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[BytearrayBase64Provider()]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=bytearray),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=bytearray),
            debug_path=debug_path
        )
    )

    assert dumper(bytearray(b'abcd')) == 'YWJjZA=='


@parametrize_bool('strict_coercion', 'debug_path')
def test_regex_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[RegexPatternProvider()]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=re.Pattern),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader(r'\w') == re.compile(r'\w')

    raises_path(
        TypeLoadError(str),
        lambda: loader(10)
    )
    raises_path(
        ValueLoadError("bad escape (end of pattern) at position 0"),
        lambda: loader('\\')
    )

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=re.Pattern),
            debug_path=debug_path,
        )
    )

    assert dumper(re.compile(r'\w')) == r'\w'
