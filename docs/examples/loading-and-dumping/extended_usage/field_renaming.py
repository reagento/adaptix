from dataclasses import dataclass
from datetime import datetime, timezone

from adaptix import Retort, name_mapping


@dataclass
class Event:
    name: str
    timestamp: datetime


retort = Retort(
    recipe=[
        name_mapping(
            Event,
            map={
                'timestamp': 'ts',
            },
        ),
    ]
)

data = {
    'name': 'SystemStart',
    'ts': '2023-05-14T00:06:33+00:00',
}
event = retort.load(data, Event)
assert event == Event(
    name='SystemStart',
    timestamp=datetime(2023, 5, 14, 0, 6, 33, tzinfo=timezone.utc),
)
assert retort.dump(event) == data
