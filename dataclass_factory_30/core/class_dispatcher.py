from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Dict, Type, Tuple, Collection

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

    def __post_init__(self):
        super().__init__()


@dataclass
class ValueDuplication(ValueError, Generic[K, V]):
    left_key: K
    right_key: K
    value: V

    def __post_init__(self):
        super().__init__()


def _check_values_uniqueness(mapping: Dict[K, V]):
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
            _check_values_uniqueness(mapping)
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

    def merge(
        self,
        other: 'ClassDispatcher[K_co, V]',
        remove: Optional[Collection[V]] = None
    ) -> 'ClassDispatcher[K_co, V]':
        if not self._mapping:
            return other

        if remove is None:
            self_copy = self._mut_copy()
        else:
            self_copy = self.remove_values(remove)._mut_copy()

        inv_map = {v: k for k, v in self_copy._mapping.items()}

        for key, value in other.items():
            if remove is not None and value in remove:
                continue

            if key in self_copy.keys():
                raise KeyDuplication(
                    key=key,
                    left_value=self_copy._mapping[key],
                    right_value=value,
                )

            if value in inv_map:
                old_self_key = inv_map[value]
                del self_copy._mapping[old_self_key]
                self_copy._mapping[key] = value
            else:
                self_copy._mapping[key] = value

        return self_copy

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

    def keys(self) -> Collection[Type[K_co]]:
        return self._mapping.keys()

    def items(self) -> Collection[Tuple[Type[K_co], V]]:
        return self._mapping.items()

    def __repr__(self):
        return f'{type(self).__qualname__}({self._mapping})'
