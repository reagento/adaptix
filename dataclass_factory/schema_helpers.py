from datetime import datetime
from uuid import UUID

from .schema import Schema

try:
    isotime_schema = Schema(
        parser=datetime.fromisoformat,  # type: ignore
        serializer=datetime.isoformat
    )
except AttributeError:
    pass


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
    serializer=datetime.timestamp
)

uuid_schema = Schema(
    serializer=UUID.__str__,
    parser=UUID
)
