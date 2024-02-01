from typing import (
    AbstractSet,
    Callable,
    Collection,
    Dict,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    ValuesView,
    overload,
    runtime_checkable,
)

from .common import VarTuple

K = TypeVar('K', bound=Hashable)
V = TypeVar('V')
_VT_co = TypeVar("_VT_co", covariant=True)


@runtime_checkable
class SupportsKeysAndGetItem(Protocol[K, _VT_co]):
    def keys(self) -> Iterable[K]:
        ...

    def __getitem__(self, __key: K) -> _VT_co:
        ...


class UnrewritableDict(Dict[K, V], Generic[K, V]):
    def __setitem__(self, key, value):
        if key in self:
            old_value = self[key]
            if value is not old_value:
                raise KeyError(f"Key {key!r} can not be overwritten")
        else:
            super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, SupportsKeysAndGetItem):
                for k in obj.keys():
                    self[k] = obj[k]
            else:
                for k, v in obj:
                    self[k] = v

        if len(args) != 0:
            raise ValueError

        for k, v in kwargs.items():
            self[k] = v

    def __repr__(self):
        return f"{type(self).__name__}({super().__repr__()})"


K_co = TypeVar('K_co', covariant=True)


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
        If the key does not exist, it will return
        the value of the closest superclass otherwise raise KeyError
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
H = TypeVar('H', bound=Hashable)


class ClassMap(Generic[H]):
    __slots__ = ('_mapping', '_hash')

    def __init__(self, *values: H):
        # need stable order for hash calculation
        self._mapping: Mapping[Type[H], H] = {
            type(value): value
            for value in sorted(values, key=lambda v: type(v).__qualname__)
        }
        self._hash = hash(tuple(self._mapping.values()))

    def __getitem__(self, item: Type[D]) -> D:
        return self._mapping[item]  # type: ignore[index,return-value]

    def __iter__(self) -> Iterator[Type[H]]:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)

    def __contains__(self, item):
        return item in self._mapping

    def has(self, *classes: Type[H]) -> bool:
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

    def keys(self) -> KeysView[Type[H]]:
        return self._mapping.keys()

    def values(self) -> ValuesView[H]:
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
        return self._hash

    def __repr__(self):
        args_str = ', '.join(repr(v) for v in self._mapping.values())
        return f'{type(self).__qualname__}({args_str})'

    def add(self: CM, *values: H) -> CM:
        return type(self)(*self._mapping.values(), *values)

    def discard(self: CM, *classes: Type[H]) -> CM:
        return type(self)(
            value for key, value in self._mapping.items()
            if key not in classes
        )


T = TypeVar('T')
StackT = TypeVar('StackT', bound='ImmutableStack')


class ImmutableStack(Sequence[T], Generic[T]):
    __slots__ = ('_tuple', )

    def __init__(self, *args: T):
        self._tuple = args

    @classmethod
    def from_tuple(cls: Type[StackT], tpl: VarTuple[T]) -> StackT:
        self = cls.__new__(cls)
        self._tuple = tpl
        return self

    @classmethod
    def from_iter(cls: Type[StackT], iterable: Iterable[T]) -> StackT:
        return cls.from_tuple(tuple(iterable))

    @property
    def last(self) -> T:
        return self[-1]

    def __repr__(self):
        return f"{type(self).__name__}{self._tuple!r}"

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self: StackT, index: slice) -> StackT:
        ...

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._tuple[index]
        return self.from_tuple(self._tuple[index])

    def __len__(self):
        return len(self._tuple)

    def __hash__(self):
        return hash(self._tuple)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self._tuple == other._tuple
        return NotImplemented

    def __iter__(self) -> Iterator[T]:
        return iter(self._tuple)

    def append_with(self: StackT, item: T) -> StackT:
        return self.from_tuple(self._tuple + (item, ))
