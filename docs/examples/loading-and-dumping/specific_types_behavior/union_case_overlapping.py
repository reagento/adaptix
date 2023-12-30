from dataclasses import dataclass
from typing import Union

from adaptix import Retort


@dataclass
class Cat:
    name: str
    breed: str


@dataclass
class Dog:
    name: str
    breed: str


retort = Retort()
retort.load({'name': 'Tardar Sauce', 'breed': 'mixed'}, Union[Cat, Dog])
