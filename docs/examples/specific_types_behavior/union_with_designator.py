from dataclasses import dataclass
from typing import Union, Literal

from adaptix import Retort, name_mapping, P


@dataclass
class Cat:
    name: str
    breed: str

    kind: Literal['cat'] = 'cat'


@dataclass
class Dog:
    name: str
    breed: str

    kind: Literal['dog'] = 'dog'


retort = Retort(
    recipe=[
        name_mapping(
            P[Cat, Dog],
            omit_default=False,
        ),
    ],
)
data = {'name': 'Tardar Sauce', 'breed': 'mixed', 'kind': 'cat'}
cat = retort.load(data, Union[Cat, Dog])
assert cat == Cat(name='Tardar Sauce', breed='mixed')
assert retort.dump(cat) == data
