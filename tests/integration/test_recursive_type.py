from dataclasses import dataclass
from typing import Optional

from adaptix import Retort


@dataclass
class Foo:
    a: int
    next: Optional['Foo'] = None


retort = Retort()


def test_dataclass():
    assert retort.dump(Foo(a=1)) == {'a': 1, 'next': None}
    assert retort.dump(Foo(a=1, next=Foo(a=2))) == {'a': 1, 'next': {'a': 2, 'next': None}}
    assert (
        retort.dump(Foo(a=1, next=Foo(a=2, next=Foo(a=3))))
        ==
        {'a': 1, 'next': {'a': 2, 'next': {'a': 3, 'next': None}}}
    )

