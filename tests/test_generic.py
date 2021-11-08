from dataclasses import dataclass
from typing import Generic, TypeVar, List
from unittest import TestCase

from dataclass_factory import Factory, Schema

T = TypeVar('T')
V = TypeVar('V')


@dataclass
class Foo(Generic[T]):
    value: T


@dataclass
class FakeFoo(Generic[T]):
    value: str


@dataclass
class FooBar(Generic[T, V]):
    value: T
    value2: V
    value3: T


@dataclass
class FooBaz(Generic[T]):
    foo: Foo[T]


@dataclass
class ListBaz(Generic[T]):
    foo: List[T]


class TestGeneric(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    def test_simple_int(self):
        foo = Foo[int](1)
        foo_serial = {"value": 1}
        self.assertEqual(self.factory.load(foo_serial, Foo[int]), foo)
        self.assertEqual(self.factory.dump(foo, Foo[int]), foo_serial)

    def test_list_field(self):
        foo = ListBaz[int]([1])
        foo_serial = {"foo": [1]}
        self.assertEqual(self.factory.load(foo_serial, ListBaz[int]), foo)
        self.assertEqual(self.factory.dump(foo, ListBaz[int]), foo_serial)

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
            FakeFoo[str]: Schema(name_mapping={"value": "s"}),
            FakeFoo: Schema(name_mapping={"value": "v"}),
        })
        data = {"v": "hello", "i": 42, "s": "SSS"}
        self.assertEqual(factory.load(data, FakeFoo[str]), FakeFoo("SSS"))
        self.assertEqual(factory.load(data, FakeFoo[int]), FakeFoo("hello"))

    def test_schema_dump(self):
        factory = Factory(schemas={
            FakeFoo[str]: Schema(name_mapping={"value": "s"}),
            FakeFoo: Schema(name_mapping={"value": "v"}),
        })
        # self.assertEqual(factory.dump(FakeFoo("hello"), FakeFoo[str]), {"s": "hello"})
        self.assertEqual(factory.dump(FakeFoo("hello")), {"v": "hello"})

    def test_schema_dump_inner(self):
        factory = Factory(schemas={
            FooBaz[int]: Schema(name_mapping={"foo": "bar"}),
            Foo[int]: Schema(name_mapping={"value": "v"}),
        })
        self.assertEqual(factory.dump(FooBaz(Foo(1)), FooBaz[int]), {"bar": {"v": 1}})
