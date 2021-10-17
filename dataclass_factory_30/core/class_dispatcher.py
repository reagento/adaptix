from typing import Generic, TypeVar, Optional, Dict, Type, Tuple, Collection, Iterator, Hashable, AbstractSet, List

K_co = TypeVar('K_co', covariant=True, bound=Hashable)
K = TypeVar('K', bound=Hashable)
V = TypeVar('V', bound=Hashable)


def _get_kinship(sub_cls: type, cls: type) -> int:
    return sub_cls.mro().index(cls)


class ClassDispatcher(Generic[K_co, V]):
    """Class Dispatcher is a special immutable container
    that stores classes and values associated with them.
    If you lookup for the value that is not presented in keys
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
        try:
            return self._mapping[key]
        except KeyError:
            min_kinship = None
            mk_value = None

            for cls, value in self._mapping.items():
                try:
                    kinship = _get_kinship(key, cls)
                except ValueError:
                    continue

                if min_kinship is None or kinship < min_kinship:
                    min_kinship = kinship
                    mk_value = value

            if min_kinship is None:
                raise KeyError

            return mk_value  # type: ignore

    def _mut_copy(self):
        cp = type(self)()
        cp._mapping = self._mapping.copy()
        return cp

    # require Container + Iterable
    def remove_values(self, values: Collection[V]) -> 'ClassDispatcher[K_co, V]':
        self_copy = self._mut_copy()
        for key, value in self_copy._mapping.items():
            if value in values:
                del self_copy._mapping[key]

        return self_copy

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


def _remove_superclasses(source: List[type], other: List[type]):
    """
    Remove all elements from :param source:
    that is superclass of any of element from :param other:
    """
    i = 0
    while i < len(source):
        source_item = source[i]
        for other_item in other:
            if issubclass(other_item, source_item):  # noqa
                source.pop(i)
                break
        else:
            i += 1


# It's not a KeysView because __iter__ of KeysView must returns a Iterator[K_co]
# but there is no inverse of Type[]
class ClassDispatcherKeysView(Generic[K_co]):
    def __init__(self, keys: AbstractSet[Type[K_co]]):
        self._keys = keys

    def bind(self, value: V) -> ClassDispatcher[K_co, V]:
        """Creates a ClassDispatcher
         whose elements all point to the same value
        """
        return ClassDispatcher({k: value for k in self._keys})

    def intersect(self, other: 'ClassDispatcherKeysView[K_co]') -> 'ClassDispatcherKeysView[K_co]':
        """Returns ClassDispatcherKeysView which contains keys
        covered by both keys view
        """
        self_keys = list(self._keys)
        other_keys = list(other._keys)
        _remove_superclasses(self_keys, other_keys)
        _remove_superclasses(other_keys, self_keys)

        result = set(self_keys)
        result.update(other_keys)
        return ClassDispatcherKeysView(result)

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[Type[K_co]]:
        return iter(self._keys)

    def __contains__(self, element: object) -> bool:
        return element in self._keys

    def __repr__(self):
        keys = ", ".join(repr(k) for k in self._keys)
        return f'{type(self).__qualname__}({keys})'
