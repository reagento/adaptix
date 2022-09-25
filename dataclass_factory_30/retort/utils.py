from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import copy
from typing import Any, Generator, TypeVar, final

C = TypeVar('C', bound='Cloneable')


class Cloneable(ABC):
    @abstractmethod
    def _calculate_derived(self):
        ...

    @contextmanager
    @final
    def _clone(self: C) -> Generator[C, Any, Any]:
        self_copy = copy(self)
        yield self_copy
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
