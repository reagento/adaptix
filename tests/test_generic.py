#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from typing import TypeVar, Generic

from dataclass_factory import Factory

T = TypeVar('T')
V = TypeVar('V')


@dataclass
class Foo(Generic[T]):
    value: T


@dataclass
class FooBar(Generic[T, V]):
    value: T
    value2: V
    value3: T


class TestGeneric(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    def test_simple_int(self):
        foo = Foo[int](1)
        foo_serial = {"value": 1}
        self.assertEqual(self.factory.load(foo_serial, Foo[int]), foo)
        self.assertEqual(self.factory.dump(foo, Foo[int]), foo_serial)

    def test_simple_str(self):
        foo = Foo[str]("hello")
        foo_serial = {"value": "hello"}
        self.assertEqual(self.factory.load(foo_serial, Foo[str]), foo)
        self.assertEqual(self.factory.dump(foo, Foo[str]), foo_serial)

    def test_implicit_simple(self):
        foo = Foo(1)
        foo_serial = {"value": 1}
        self.assertEqual(self.factory.load(foo_serial, Foo[int]), foo)
        self.assertEqual(self.factory.dump(foo), foo_serial)

    def test_two_vars(self):
        foo = FooBar(1, "str", 3)
        foo_serial = {"value": 1, "value2": "str", "value3": 3}
        self.assertEqual(self.factory.load(foo_serial, FooBar[int, str]), foo)
        self.assertEqual(self.factory.dump(foo), foo_serial)
