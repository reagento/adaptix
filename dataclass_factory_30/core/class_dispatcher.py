from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Dict, Iterable, Type, Tuple

K_co = TypeVar('K_co', covariant=True)
K = TypeVar('K')
V = TypeVar('V')


def _get_kinship(sub_cls: type, cls: type) -> int:
    return sub_cls.mro().index(cls)


@dataclass
class KeyDuplication(Exception, Generic[K, V]):
    key: K
    left_value: V
    right_value: V


@dataclass
class ValueDuplication(ValueError, Generic[K, V]):
    left_key: K
    right_key: K
    value: V


def check_values_uniqueness(mapping: Dict[K, V]):
    inv_mapping: Dict[V, K] = {}
    for key, value in mapping.items():
        if value in inv_mapping:
            raise ValueDuplication(
                left_key=inv_mapping[value], right_key=key, value=value
            )
        inv_mapping[value] = key


class ClassDispatcher(Generic[K_co, V]):
    """ClassDispatcher is a special container
    """
    __slots__ = ('_mapping',)

    def __init__(self, mapping: Optional[Dict[Type[K_co], V]] = None):
        if mapping is None:
            self._mapping: Dict[Type[K_co], V] = {}
        else:
            check_values_uniqueness(mapping)
            self._mapping = mapping

    def __getitem__(self, key: Type[K_co]) -> V:
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

    def merge_overwrite(self, other: 'ClassDispatcher[K_co, V]') -> 'ClassDispatcher[K_co, V]':
        mapping = self._mapping

        for key, value in other._mapping.items():
            mapping[key] = value

        return type(self)(mapping)

    def merge_exclusive(self, other: 'ClassDispatcher[K_co, V]') -> 'ClassDispatcher[K_co, V]':
        mapping = self._mapping

        for key, value in other._mapping.items():
            if key in mapping:
                raise KeyDuplication(
                    key=key, left_value=mapping[key], right_value=value
                )
            else:
                mapping[key] = value

        return type(self)(mapping)

    def values(self) -> Iterable[V]:
        return self._mapping.values()

    def keys(self) -> Iterable[Type[K_co]]:
        return self._mapping.keys()

    def items(self) -> Iterable[Tuple[Type[K_co], V]]:
        return self._mapping.items()

    def __repr__(self):
        return f'{type(self).__qualname__}({self._mapping})'
