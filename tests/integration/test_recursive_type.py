from dataclasses import dataclass
from typing import Optional

from adaptix import Retort


@dataclass
class Foo:
    a: int
    next: Optional['Foo'] = None


retort = Retort()


def test_simple():
    dumped_data = {'a': 1, 'next': None}
    loaded_data = Foo(a=1)
    assert retort.dump(loaded_data) == dumped_data
    assert retort.load(dumped_data, Foo) == loaded_data

    dumped_data = {'a': 1, 'next': {'a': 2, 'next': None}}
    loaded_data = Foo(a=1, next=Foo(a=2))
    assert retort.dump(loaded_data) == dumped_data
    assert retort.load(dumped_data, Foo) == loaded_data

    dumped_data = {'a': 1, 'next': {'a': 2, 'next': {'a': 3, 'next': None}}}
    loaded_data = Foo(a=1, next=Foo(a=2, next=Foo(a=3)))
    assert retort.dump(loaded_data) == dumped_data
    assert retort.load(dumped_data, Foo) == loaded_data


@dataclass
class Tree:
    left: Optional['Tree'] = None
    right: Optional['Tree'] = None


def test_several_recursive_types():
    dumped_data = {
        'left': {
            'left': {'left': None, 'right': None},
            'right': {'left': None, 'right': None}
        },
        'right': {'left': None, 'right': None}
    }
    loaded_data = Tree(left=Tree(left=Tree(), right=Tree()), right=Tree())
    assert retort.dump(loaded_data) == dumped_data
    assert retort.load(dumped_data, Tree) == loaded_data
