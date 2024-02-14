import itertools
import sys
import warnings
from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import copy
from typing import (
    Any,
    Callable,
    Collection,
    Generator,
    Iterable,
    Iterator,
    List,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    final,
    overload,
)

from .feature_requirement import HAS_NATIVE_EXC_GROUP, HAS_PY_310

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

if HAS_PY_310:
    pairs = itertools.pairwise  # pylint: disable=invalid-name
else:
    def pairs(iterable: Iterable[T]) -> Iterable[Tuple[T, T]]:  # type: ignore[no-redef]
        it = iter(iterable)
        try:
            prev = next(it)
        except StopIteration:
            return

        for current in it:
            yield prev, current
            prev = current


class Omitted(metaclass=SingletonMeta):
    def __bool__(self):
        raise TypeError('Omitted() can not be used in boolean context')


Omittable = Union[T, Omitted]


ComparableSeqT = TypeVar('ComparableSeqT', bound='ComparableSequence')


class ComparableSequence(Protocol[T]):
    def __lt__(self, __other: T) -> bool:
        ...

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self: ComparableSeqT, index: slice) -> ComparableSeqT:
        ...

    def __iter__(self) -> Iterator[T]:
        ...

    def __len__(self) -> int:
        ...

    def __contains__(self, value: object) -> bool:
        ...

    def __reversed__(self) -> Iterator[T]:
        ...


def get_prefix_groups(
    values: Collection[ComparableSeqT],
) -> Collection[Tuple[ComparableSeqT, Iterable[ComparableSeqT]]]:
    groups: List[Tuple[ComparableSeqT, List[ComparableSeqT]]] = []
    sorted_values = iter(sorted(values))
    current_group: List[ComparableSeqT] = []
    try:
        prefix = next(sorted_values)
    except StopIteration:
        return []

    for value in sorted_values:
        if value[:len(prefix)] == prefix:
            current_group.append(value)
        else:
            if current_group:
                groups.append((prefix, current_group))
                current_group = []
            prefix = value

    if current_group:
        groups.append((prefix, current_group))
    return groups


def copy_exception_dunders(source: BaseException, target: BaseException) -> None:
    if hasattr(source, '__notes__'):
        target.__notes__ = source.__notes__
    elif hasattr(target, '__notes__'):
        delattr(target, '__notes__')
    target.__context__ = source.__context__
    target.__cause__ = source.__cause__
    target.__traceback__ = source.__traceback__
    target.__suppress_context__ = source.__suppress_context__


if HAS_NATIVE_EXC_GROUP:
    def add_note(exc: BaseException, note: str) -> None:
        exc.add_note(note)
else:
    def add_note(exc: BaseException, note: str) -> None:
        if hasattr(exc, '__notes__'):
            exc.__notes__.append(note)
        else:
            exc.__notes__ = [note]


ClassT = TypeVar('ClassT', bound=type)


def with_module(module: str) -> Callable[[ClassT], ClassT]:
    def decorator(cls):
        cls.__module__ = module
        return cls

    return decorator


def create_deprecated_alias_getter(module_name, old_name_to_new_name):
    def __getattr__(name):
        if name not in old_name_to_new_name:
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

        new_name = old_name_to_new_name[name]
        warnings.warn(
            f"Name {name!r} is deprecated, use {new_name!r} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(sys.modules[module_name], new_name)

    return __getattr__
