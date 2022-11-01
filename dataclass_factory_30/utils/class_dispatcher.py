from typing import AbstractSet, Collection, Dict, Generic, Hashable, Iterator, Optional, Tuple, Type, TypeVar

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
        value of the closest superclass or raise KeyError
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
