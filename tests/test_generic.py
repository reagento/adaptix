#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from unittest import TestCase

from typing import TypeVar, Generic

from dataclass_factory import Factory, Schema

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


@dataclass
class FooBaz(Generic[T]):
    foo: Foo[T]


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

    def test_inner(self):
        baz = FooBaz(Foo(1))
        baz_serial = {"foo": {"value": 1}}
        self.assertEqual(self.factory.load(baz_serial, FooBaz[int]), baz)
        self.assertEqual(self.factory.dump(baz), baz_serial)

    def test_inner2(self):
        baz = Foo(FooBaz(Foo(1)))
        baz_serial = {"value": {"foo": {"value": 1}}}
        self.assertEqual(self.factory.load(baz_serial, Foo[FooBaz[int]]), baz)
        self.assertEqual(self.factory.dump(baz, Foo[FooBaz[int]]), baz_serial)
        self.assertEqual(self.factory.dump(baz), baz_serial)

    def test_schema_load(self):
        factory = Factory(schemas={
            Foo[str]: Schema(name_mapping={"value": "s"}),
            Foo[int]: Schema(name_mapping={"value": "i"}),
        })
        data = {"s": "hello", "i": 42}
        self.assertEqual(factory.load(data, Foo[str]), Foo("hello"))
        self.assertEqual(factory.load(data, Foo[int]), Foo(42))

    def test_schema_dump(self):
        factory = Factory(schemas={
            Foo[str]: Schema(name_mapping={"value": "s"}),
            Foo[int]: Schema(name_mapping={"value": "i"}),
        })
        self.assertEqual(factory.dump(Foo(42)), {"i": 42})
        self.assertEqual(factory.dump(Foo("hello")), {"s": "hello"})
