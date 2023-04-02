from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import copy
from typing import (
    AbstractSet,
    Any,
    Callable,
    Collection,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    ValuesView,
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


K_co = TypeVar('K_co', covariant=True)
V = TypeVar('V')


class ClassDispatcher(Generic[K_co, V]):
    """Class Dispatcher is a special immutable container
    that stores classes and values associated with them.
    If you look up for the value that is not presented in keys
    ClassDispatcher will return the value of the closest superclass.
    """
    __slots__ = ('_mapping',)

    def __init__(self, mapping: Optional[Mapping[Type[K_co], V]] = None):
        self._mapping: Dict[Type[K_co], V] = {} if mapping is None else dict(mapping)

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

        raise KeyError(key)

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


CM = TypeVar('CM', bound='ClassMap')
D = TypeVar('D')


class ClassMap(Generic[T]):
    __slots__ = ('_mapping', )

    def __init__(self, *values: T):
        self._mapping: Mapping[Type[T], T] = {type(value): value for value in values}

    def __getitem__(self, item: Type[D]) -> D:
        return self._mapping[item]  # type: ignore[index,return-value]

    def __iter__(self) -> Iterator[Type[T]]:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)

    def __contains__(self, item):
        return item in self._mapping

    def has(self, *classes: Type[T]) -> bool:
        return all(key in self._mapping for key in classes)

    def get_or_raise(
        self,
        key: Type[D],
        exception_factory: Callable[[], Union[BaseException, Type[BaseException]]],
    ) -> D:
        try:
            return self._mapping[key]  # type: ignore[index,return-value]
        except KeyError:
            raise exception_factory() from None

    def keys(self) -> KeysView[Type[T]]:
        return self._mapping.keys()

    def values(self) -> ValuesView[T]:
        return self._mapping.values()

    def __eq__(self, other):
        if isinstance(other, ClassMap):
            return self._mapping == other._mapping
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ClassMap):
            return self._mapping != other._mapping
        return NotImplemented

    def __hash__(self):
        return hash((key, value) for key, value in self._mapping.items())

    def __repr__(self):
        return f'{type(self).__qualname__}({self._mapping!r})'

    def _with_new_mapping(self: CM, mapping: Mapping[Type[T], T]) -> CM:
        self_copy = copy(self)
        self_copy._mapping = mapping  # pylint: disable=protected-access
        return self_copy

    def add(self: CM, *values: T) -> CM:
        return self._with_new_mapping(
            {**self._mapping, **{type(value): value for value in values}}
        )

    def discard(self: CM, *classes: Type[T]) -> CM:
        return self._with_new_mapping(
            {
                key: value for key, value in self._mapping.items()
                if key not in classes
            }
        )
