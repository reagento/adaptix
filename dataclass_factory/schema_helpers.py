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

unixtime_schema = Schema(
    parser=datetime.fromtimestamp,
    serializer=datetime.timestamp
)

uuid_schema = Schema(
    serializer=UUID.__str__,
    parser=UUID
)
