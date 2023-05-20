from dataclasses import dataclass
from adaptix import Retort, name_mapping


@dataclass
class Interval:
    from_: int
    to_: int


retort = Retort(
    recipe=[
        name_mapping(
            Interval,
            trim_trailing_underscore=False,
        ),
    ]
)

data = {
    'from_': 10,
    'to_': 20,
}
event = retort.load(data, Interval)
assert event == Interval(from_=10, to_=20)
assert retort.dump(event) == data
