from dataclasses import dataclass
from datetime import datetime

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
            as_list=True,
        ),
    ]
)


action = Action(
    user_id=23,
    kind='click',
    timestamp=datetime(2023, 5, 20, 15, 58, 23, 410366),
)
data = [
    23,
    'click',
    '2023-05-20T15:58:23.410366',
]
assert retort.dump(action) == data
assert retort.load(data, Action) == action
