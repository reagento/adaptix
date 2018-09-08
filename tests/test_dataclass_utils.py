#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum
from typing import Optional, List, Union, Tuple, Dict, FrozenSet, Set, Any
from unittest import TestCase

from dataclasses import dataclass, field

from dataclass_factory import parse


@dataclass
class D:
    a: int
    b: int = field(init=False, default=1)
    c: str = "def_value"


class E(Enum):
    one = 1
    hello = "hello"


@dataclass
class D2:
    d: D
    e: E


@dataclass
class D3:
    id_: int
    none: Optional[str] = None
    lst: Optional[List[E]] = None


@dataclass
class DUnion:
    value: Union[str, int, List[E]]


class Test1(TestCase):

    def test_enum(self):
        self.assertEqual(parse("hello", E), E.hello)
        self.assertEqual(parse(1, E), E.one)
        self.assertEqual(parse(E.one, E), E.one)

    def test_simple_dataclass(self):
        data = {
            "a": 1
        }
        self.assertEqual(parse(data, D), D(a=1))

        data = {
            "a": 1,
            "c": "value",
        }
        self.assertEqual(parse(data, D), D(a=1, c="value"))

    def test_complex_dataclass(self):
        data = {
            "d": {
                "a": 1,
                "c": "value",
            },
            "e": "hello"
        }
        self.assertEqual(parse(data, D2), D2(d=D(a=1, c="value"), e=E.hello))

    def test_configs(self):
        data = {
            "id": 1,
            "none": None
        }
        self.assertEqual(
            parse(data, D3, trim_trailing_underscore=True),
            D3(id_=1, none=None)
        )

    def test_typing(self):
        data = {
            "id": 1,
            "none": "hello"
        }
        self.assertEqual(
            parse(data, D3),
            D3(id_=1, none="hello")
        )

        data = {
            "id": 1,
            "lst": None
        }
        self.assertEqual(
            parse(data, D3),
            D3(id_=1, lst=None)
        )

        data = {
            "id": 1,
            "lst": [1, "hello"]
        }
        self.assertEqual(
            parse(data, D3),
            D3(id_=1, lst=[E.one, E.hello])
        )

    def test_union(self):
        data = {
            "value": "hello"
        }
        self.assertEqual(parse(data, DUnion), DUnion("hello"))
        data = {
            "value": 1
        }
        self.assertEqual(parse(data, DUnion), DUnion(1))
        data = {
            "value": [1]
        }
        self.assertEqual(parse(data, DUnion), DUnion([E.one]))

    def test_list(self):
        self.assertEqual(parse(["q"], List[str]), ["q"])
        self.assertEqual(parse(["q"], Tuple[str]), ("q",))
        self.assertNotEqual(parse(["q"], List[str]), ("q",))

    def test_dict(self):
        self.assertEqual(parse({1: 2}, Dict[int, int]), {1: 2})

        x = frozenset({1, 2})
        self.assertEqual(parse({x: {"q", "w"}}, Dict[FrozenSet[int], Set[str]]), {x: {"q", "w"}})

    def test_any(self):
        self.assertEqual(parse(1, Any), 1)
        self.assertEqual(parse({1, 2}, Any), {1, 2})

    def test_noargs(self):
        self.assertEqual(parse([1, "q"], List), [1, "q"])
        self.assertEqual(parse({1: "q", "w": 2}, Dict), {1: "q", "w": 2})
