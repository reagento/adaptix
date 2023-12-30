from dataclasses import dataclass
from typing import Union

from adaptix import Retort


@dataclass
class Vehicle:
    speed: float


@dataclass
class Bike(Vehicle):
    wheel_count: int


retort = Retort()
data = {'speed': 10, 'wheel_count': 3}
assert retort.load(data, Bike) == Bike(speed=10, wheel_count=3)
assert retort.load(data, Vehicle) == Vehicle(speed=10)
retort.load(data, Union[Bike, Vehicle])  # result is undefined
