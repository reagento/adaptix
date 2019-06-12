from datetime import datetime

from .schema import Schema

try:
    isotime_schema = Schema(
        parser=datetime.fromisoformat,
        serializer=datetime.isoformat
    )
except AttributeError:
    pass

unixtime_schema = Schema(
    parser=datetime.fromtimestamp,
    serializer=datetime.timestamp
)
