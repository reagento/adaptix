from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import copy
from typing import (
    AbstractSet,
    Any,
    Collection,
    Dict,
    Generator,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    final,
)

C = TypeVar('C', bound='Cloneable')


class Cloneable(ABC):
    @abstractmethod
    def _calculate_derived(self) -> None:
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


def _singleton_hash(self) -> int:
    return hash(type(self))


def _singleton_copy(self):
    return self


def _singleton_deepcopy(self, memo):
    return self


def _singleton_new(cls):
    return cls._instance  # pylint: disable=protected-access


class SingletonMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        namespace.setdefault("__repr__", _singleton_repr)
        namespace.setdefault("__str__", _singleton_repr)
        namespace.setdefault("__hash__", _singleton_hash)
        namespace.setdefault("__copy__", _singleton_copy)
        namespace.setdefault("__deepcopy__", _singleton_deepcopy)
        namespace.setdefault("__slots__", ())
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        instance = super().__call__(cls)
        cls._instance = instance
        if '__new__' not in cls.__dict__:
            cls.__new__ = _singleton_new
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


class Omitted(metaclass=SingletonMeta):
    def __bool__(self):
        raise TypeError('Omitted() can not be used in boolean context')


Omittable = Union[T, Omitted]


K_co = TypeVar('K_co', covariant=True, bound=Hashable)
V = TypeVar('V')


class ClassDispatcher(Generic[K_co, V]):
    """Class Dispatcher is a special immutable container
    that stores classes and values associated with them.
    If you look up for the value that is not presented in keys
    ClassDispatcher will return the value of the closest superclass.
    """
    __slots__ = ('_mapping',)

    def __init__(self, mapping: Optional[Dict[Type[K_co], V]] = None):
        if mapping is None:
            self._mapping: Dict[Type[K_co], V] = {}
        else:
            self._mapping = mapping

    def dispatch(self, key: Type[K_co]) -> V:
        """Returns a value associated with the key.
        If the key does not exist it will return
        value of the closest superclass otherwise raise KeyError
        """
        for parent in key.__mro__:
            try:
                return self._mapping[parent]
            except KeyError:
                pass

        raise KeyError

    def values(self) -> Collection[V]:
        return self._mapping.values()

    def keys(self) -> 'ClassDispatcherKeysView[K_co]':
        return ClassDispatcherKeysView(self._mapping.keys())

    def items(self) -> Collection[Tuple[Type[K_co], V]]:
        return self._mapping.items()

    def __repr__(self):
        return f'{type(self).__qualname__}({self._mapping})'

    def to_dict(self) -> Dict[Type[K_co], V]:
        return self._mapping.copy()

    def __eq__(self, other):
        if isinstance(other, ClassDispatcher):
            return self._mapping == other._mapping
        return NotImplemented


# It's not a KeysView because __iter__ of KeysView must returns an Iterator[K_co]
# but there is no inverse of Type[]
class ClassDispatcherKeysView(Generic[K_co]):
    __slots__ = ('_keys',)

    def __init__(self, keys: AbstractSet[Type[K_co]]):
        self._keys = keys

    def bind(self, value: V) -> ClassDispatcher[K_co, V]:
        """Creates a ClassDispatcher
         whose elements all point to the same value
        """
        return ClassDispatcher({k: value for k in self._keys})

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[Type[K_co]]:
        return iter(self._keys)

    def __contains__(self, element: object) -> bool:
        return element in self._keys

    def __repr__(self):
        return f'{type(self).__qualname__}({self._keys!r})'
