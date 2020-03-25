from datetime import datetime, timezone

from dataclasses import dataclass

from dataclass_factory import Schema, Factory


@dataclass
class Author:
    name: str
    born_at: datetime


def parse_timestamp(data):
    print("parsing timestamp")
    return datetime.fromtimestamp(data, tz=timezone.utc)


unixtime_schema = Schema(
    parser=parse_timestamp,
    serializer=datetime.timestamp
)

factory = Factory(
    schemas={
        datetime: unixtime_schema,
    }
)
expected_author = Author("Petr", datetime(1970, 1, 2, 3, 4, 56, tzinfo=timezone.utc))
data = {'born_at': 97496, 'name': 'Petr'}
author = factory.load(data, Author)
print(author, expected_author)
assert author == expected_author

serialized = factory.dump(author)
assert data == serialized
