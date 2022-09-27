from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import copy
from typing import Any, Generator, Iterable, Tuple, TypeVar, final

C = TypeVar('C', bound='Cloneable')


class Cloneable(ABC):
    @abstractmethod
    def _calculate_derived(self):
        ...

    @contextmanager
    @final
    def _clone(self: C) -> Generator[C, Any, Any]:
        self_copy = copy(self)
        try:
            yield self_copy
        finally:
            self_copy._calculate_derived()  # pylint: disable=W0212


class ForbiddingDescriptor:
    def __init__(self):
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        raise AttributeError(f"Can not read {self._name!r} attribute")

    def __set__(self, instance, value):
        raise AttributeError(f"Can not set {self._name!r} attribute")

    def __delete__(self, instance):
        raise AttributeError(f"Can not delete {self._name!r} attribute")


def _singleton_repr(self):
    return f"{type(self).__name__}()"


class SingletonMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        namespace.setdefault("__repr__", _singleton_repr)
        namespace.setdefault("__str__", _singleton_repr)
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        instance = super().__call__(cls)
        cls._instance = instance
        return cls

    def __call__(cls):
        return cls._instance


T = TypeVar('T')


def pairs(iterable: Iterable[T]) -> Iterable[Tuple[T, T]]:
    it = iter(iterable)
    try:
        past = next(it)
    except StopIteration:
        return

    for current in it:
        yield past, current
        past = current
