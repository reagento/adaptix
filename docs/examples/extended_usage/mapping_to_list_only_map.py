from dataclasses import dataclass
from datetime import datetime, timezone

from adaptix import Retort, name_mapping


@dataclass
class Action:
    user_id: int
    kind: str
    timestamp: datetime


retort = Retort(
    recipe=[
        name_mapping(
            Action,
            map={
                'user_id': 0,
                'kind': 1,
                'timestamp': 2,
            },
        ),
    ]
)


action = Action(
    user_id=23,
    kind='click',
    timestamp=datetime(2023, 5, 20, 15, 58, 23, 410366, tzinfo=timezone.utc),
)
data = [
    23,
    'click',
    '2023-05-20T15:58:23.410366+00:00',
]
assert retort.dump(action) == data
assert retort.load(data, Action) == action
