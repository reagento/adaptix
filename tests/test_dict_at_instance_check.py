from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal
from types import FunctionType, LambdaType, CodeType, MappingProxyType, SimpleNamespace, GeneratorType, \
    CoroutineType, AsyncGeneratorType, MethodType, BuiltinFunctionType, BuiltinMethodType, WrapperDescriptorType, \
    MethodWrapperType, MethodDescriptorType, ClassMethodDescriptorType, ModuleType
from unittest import TestCase
from uuid import UUID

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
    def test_no_dict(self):
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

        self.assertTrue(instance_wont_have_dict(namedtuple('test', 'x y z')))
        self.assertTrue(instance_wont_have_dict(Decimal))
        self.assertTrue(instance_wont_have_dict(UUID))

        self.assertTrue(instance_wont_have_dict(CodeType))
        self.assertTrue(instance_wont_have_dict(MappingProxyType))

        self.assertTrue(instance_wont_have_dict(GeneratorType))
        self.assertTrue(instance_wont_have_dict(CoroutineType))
        self.assertTrue(instance_wont_have_dict(AsyncGeneratorType))
        self.assertTrue(instance_wont_have_dict(MethodType))
        self.assertTrue(instance_wont_have_dict(BuiltinFunctionType))
        self.assertTrue(instance_wont_have_dict(BuiltinMethodType))
        self.assertTrue(instance_wont_have_dict(WrapperDescriptorType))
        self.assertTrue(instance_wont_have_dict(MethodWrapperType))
        self.assertTrue(instance_wont_have_dict(MethodDescriptorType))
        self.assertTrue(instance_wont_have_dict(ClassMethodDescriptorType))

        self.assertTrue(instance_wont_have_dict(SlotsClass))

    def test_has_dict(self):
        self.assertFalse(instance_wont_have_dict(type))

        self.assertFalse(instance_wont_have_dict(FunctionType))
        self.assertFalse(instance_wont_have_dict(LambdaType))
        self.assertFalse(instance_wont_have_dict(SimpleNamespace))
        self.assertFalse(instance_wont_have_dict(ModuleType))

        self.assertFalse(instance_wont_have_dict(EmptyClass))
        self.assertFalse(instance_wont_have_dict(Dataclass))
        self.assertFalse(instance_wont_have_dict(FrozenDataclass))
        self.assertFalse(instance_wont_have_dict(SlotsWithDict))
