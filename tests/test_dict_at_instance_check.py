import sys
import unittest
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal
from types import (
    FunctionType, LambdaType,
    CodeType, MappingProxyType,
    SimpleNamespace, GeneratorType,
    CoroutineType, AsyncGeneratorType,
    MethodType, BuiltinFunctionType,
    BuiltinMethodType, ModuleType
)
from unittest import TestCase

from dataclass_factory.type_detection import instance_wont_have_dict


class EmptyClass:
    pass


@dataclass
class Dataclass:
    a: int


@dataclass(frozen=True)
class FrozenDataclass:
    a: int


class SlotsClass:
    __slots__ = ('a',)

    def __init__(self, a):
        self.a = a


class SlotsWithDict:
    __slots__ = ('a', '__dict__')

    def __init__(self, a):
        self.a = a
        self.__dict__ = {}


class TestDictAtInstanceCheck(TestCase):
    @unittest.skipUnless(sys.implementation.name == 'cpython', "requires CPython")
    def test_builtins(self):
        self.assertTrue(instance_wont_have_dict(int))
        self.assertTrue(instance_wont_have_dict(bool))

        self.assertTrue(instance_wont_have_dict(str))
        self.assertTrue(instance_wont_have_dict(bytes))

        self.assertTrue(instance_wont_have_dict(tuple))
        self.assertTrue(instance_wont_have_dict(list))
        self.assertTrue(instance_wont_have_dict(dict))
        self.assertTrue(instance_wont_have_dict(set))
        self.assertTrue(instance_wont_have_dict(frozenset))

        self.assertTrue(instance_wont_have_dict(object))

        self.assertFalse(instance_wont_have_dict(type))

        self.assertTrue(instance_wont_have_dict(CodeType))
        self.assertTrue(instance_wont_have_dict(MappingProxyType))

        self.assertTrue(instance_wont_have_dict(GeneratorType))
        self.assertTrue(instance_wont_have_dict(CoroutineType))
        self.assertTrue(instance_wont_have_dict(AsyncGeneratorType))
        self.assertTrue(instance_wont_have_dict(MethodType))
        self.assertTrue(instance_wont_have_dict(BuiltinFunctionType))
        self.assertTrue(instance_wont_have_dict(BuiltinMethodType))

        self.assertFalse(instance_wont_have_dict(FunctionType))
        self.assertFalse(instance_wont_have_dict(LambdaType))
        self.assertFalse(instance_wont_have_dict(SimpleNamespace))
        self.assertFalse(instance_wont_have_dict(ModuleType))

    def test_any_implementation(self):
        self.assertTrue(instance_wont_have_dict(SlotsClass))
        self.assertTrue(instance_wont_have_dict(namedtuple('test', 'x y z')))

        self.assertFalse(instance_wont_have_dict(EmptyClass))
        self.assertFalse(instance_wont_have_dict(Dataclass))
        self.assertFalse(instance_wont_have_dict(FrozenDataclass))
        self.assertFalse(instance_wont_have_dict(SlotsWithDict))

        self.assertTrue(instance_wont_have_dict(Decimal))
