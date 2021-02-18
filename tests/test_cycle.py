from dataclasses import dataclass
from typing import Generic, Optional, TypeVar
from unittest import TestCase

from dataclass_factory import Factory


@dataclass
class LinkedList:
    data: int
    next: "Optional[LinkedList]" = None


@dataclass
class A:
    b: "Optional[B]"


@dataclass
class B:
    a: "Optional[A]"


T = TypeVar('T')


@dataclass
class GenericLinkedList(Generic[T]):
    data: int
    next: "Optional[GenericLinkedList[T]]" = None


class TestGeneric(TestCase):
    def setUp(self) -> None:
        self.factory = Factory()

    def test_self(self):
        linked = LinkedList(1, LinkedList(2))
        serial = {"data": 1, "next": {"data": 2, "next": None}}
        self.assertEqual(self.factory.dump(linked), serial)
        self.assertEqual(self.factory.load(serial, LinkedList), linked)

    def test_self_generic(self):
        linked = GenericLinkedList(1, GenericLinkedList(2))
        serial = {"data": 1, "next": {"data": 2, "next": None}}
        self.assertEqual(self.factory.dump(linked), serial)
        self.assertEqual(self.factory.load(serial, GenericLinkedList[int]), linked)

    def test_two_classes(self):
        a = A(B(A(None)))
        serial = {"b": {"a": {"b": None}}}
        self.assertEqual(self.factory.dump(a), serial)
        self.assertEqual(self.factory.load(serial, A), a)
