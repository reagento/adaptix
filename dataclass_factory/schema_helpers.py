import decimal
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Type
from uuid import UUID

from .common import T, AbstractFactory, Parser
from .schema import Schema

COMMON_SCHEMAS = {}
try:
    isodatetime_schema = Schema(
        parser=datetime.fromisoformat,  # type: ignore
        serializer=datetime.isoformat,
    )
    COMMON_SCHEMAS[datetime] = isodatetime_schema
    isodate_schema = Schema(
        parser=date.fromisoformat,
        serializer=date.isoformat
    )
    COMMON_SCHEMAS[date] = isodate_schema
    isotime_schema = Schema(
        parser=time.fromisoformat,
        serializer=time.isoformat
    )
    COMMON_SCHEMAS[time] = isotime_schema
except AttributeError:
    pass

timedelta_schema = Schema(
    parser=lambda x: timedelta(seconds=x),
    serializer=lambda x: x.seconds
)
COMMON_SCHEMAS[timedelta] = timedelta_schema


def _parse_decimal(value):
    try:
        return decimal.Decimal(value)
    except decimal.InvalidOperation as e:
        raise ValueError from e


decimal_schema = Schema(
    parser=_parse_decimal,
    serializer=lambda x: format(x, "f"),
)
COMMON_SCHEMAS[decimal.Decimal] = decimal_schema
path_schema = Schema(
    parser=Path,
    serializer=str,
)
COMMON_SCHEMAS[Path] = path_schema


def type_checker(value, field="type", pre_parse=None):
    def check_type(data):
        if value != data[field]:
            raise ValueError
        if pre_parse:
            return pre_parse(data)
        return data

    return check_type


unixtime_schema = Schema(
    parser=datetime.fromtimestamp,
    serializer=datetime.timestamp,
)

uuid_schema = Schema(
    serializer=UUID.__str__,
    parser=UUID,
)
COMMON_SCHEMAS[UUID] = uuid_schema


def _stub(data: T) -> T:
    return data


stub_schema = Schema(
    parser=_stub,
    serializer=_stub,
)


class ClsCheckSchema(Schema[T]):
    serializer = _stub

    def get_parser(self,
                   cls: Type[T],
                   stacked_factory: AbstractFactory,
                   debug_path: bool) -> Parser[T]:
        def cls_check_parser(data):
            if isinstance(data, cls):
                return data
            raise TypeError(f'Argument must be {cls.__name__}')

        return cls_check_parser
