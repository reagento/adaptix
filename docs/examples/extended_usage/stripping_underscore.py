from dataclasses import dataclass
from adaptix import Retort


@dataclass
class Interval:
    from_: int
    to_: int


retort = Retort()

data = {
    'from': 10,
    'to': 20,
}
event = retort.load(data, Interval)
assert event == Interval(from_=10, to_=20)
assert retort.dump(event) == data
