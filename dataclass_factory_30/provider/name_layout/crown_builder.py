from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import groupby
from typing import Dict, Generic, Mapping, NoReturn, Sequence, TypeVar, Union, cast

from dataclass_factory_30.provider.model.crown_definitions import (
    BaseDictCrown,
    BaseListCrown,
    CrownPath,
    DictExtraPolicy,
    InpDictCrown,
    InpListCrown,
    LeafBaseCrown,
    LeafInpCrown,
    LeafOutCrown,
    ListExtraPolicy,
    OutDictCrown,
    OutListCrown,
    Sieve,
)
from dataclass_factory_30.provider.name_layout.base import Key, Path, PathsTo


class InconsistentPathElement(TypeError):
    def __init__(self, pre_path: Path, self_item: Key, other_item: Key):
        self.pre_path = pre_path
        self.self_item = self_item
        self.other_item = other_item


class PathComparator:
    __slots__ = ('path', )

    def __init__(self, path: CrownPath):
        self.path = path

    def __lt__(self, other):  # pylint: disable=inconsistent-return-statements
        try:
            return self.path < other
        except TypeError:
            self._fallback(other)

    def _fallback(self, other) -> NoReturn:
        if not isinstance(other, tuple):
            raise TypeError

        for i, (self_item, other_item) in enumerate(zip(self.path, other)):
            try:
                self_item < other_item  # noqa: B015
            except TypeError:
                raise InconsistentPathElement(
                    pre_path=self.path[:i],
                    self_item=self_item,
                    other_item=other_item,
                ) from None

        raise RuntimeError


LeafCr = TypeVar('LeafCr', bound=LeafBaseCrown)
DictCr = TypeVar('DictCr', bound=BaseDictCrown)
ListCr = TypeVar('ListCr', bound=BaseListCrown)


@dataclass
class PathWithLeaf(Generic[LeafCr]):
    path: CrownPath
    leaf: LeafCr


PathedLeafs = Sequence[PathWithLeaf[LeafCr]]


class BaseCrownBuilder(ABC, Generic[LeafCr, DictCr, ListCr]):
    def build_crown(self, path_to_leaf: PathsTo[LeafCr]) -> Union[DictCr, ListCr]:
        paths_with_leafs = [PathWithLeaf(path, leaf) for path, leaf in path_to_leaf.items()]
        paths_with_leafs.sort(key=lambda x: PathComparator(x.path))
        return cast(Union[DictCr, ListCr], self._build_crown(paths_with_leafs, 0))

    def _build_crown(self, leaf_to_path: PathedLeafs[LeafCr], path_offset: int) -> Union[LeafCr, DictCr, ListCr]:
        try:
            first = leaf_to_path[path_offset]
        except IndexError:
            if len(leaf_to_path) != 1:
                raise ValueError
            return leaf_to_path[0].leaf

        if isinstance(first, str):
            return self._make_dict_crown(leaf_to_path, path_offset)
        if isinstance(first, int):
            return self._make_list_crown(leaf_to_path, path_offset)
        raise RuntimeError

    def _get_dict_crown_map(
        self,
        leaf_to_path: PathedLeafs[LeafCr],
        path_offset: int,
    ) -> Mapping[str, Union[LeafCr, DictCr, ListCr]]:
        return {
            cast(str, key): self._build_crown(list(path_group), path_offset + 1)
            for key, path_group in groupby(leaf_to_path, lambda x: x.path[path_offset])
        }

    @abstractmethod
    def _make_dict_crown(self, leaf_to_path: PathedLeafs[LeafCr], path_offset: int) -> DictCr:
        ...

    def _get_list_crown_map(
        self,
        leaf_to_path: PathedLeafs[LeafCr],
        path_offset: int,
    ) -> Sequence[Union[LeafCr, DictCr, ListCr]]:
        grouped_paths = [
            list(grouped_paths)
            for key, grouped_paths in groupby(leaf_to_path, lambda x: x.path[path_offset])
        ]
        if len(grouped_paths) != leaf_to_path[-1].path[path_offset]:
            raise ValueError("Found gaps at ")
        return [
            self._build_crown(path_group, path_offset + 1)
            for path_group in grouped_paths
        ]

    @abstractmethod
    def _make_list_crown(self, leaf_to_path: PathedLeafs[LeafCr], path_offset: int) -> ListCr:
        ...


class InpCrownBuilder(BaseCrownBuilder[LeafInpCrown, InpDictCrown, InpListCrown]):
    def __init__(self, extra_policies: PathsTo[DictExtraPolicy]):
        self.extra_policies = extra_policies

    def _make_dict_crown(self, leaf_to_path: PathedLeafs[LeafInpCrown], path_offset: int) -> InpDictCrown:
        return InpDictCrown(
            map=self._get_dict_crown_map(leaf_to_path, path_offset),
            extra_policy=self.extra_policies[leaf_to_path[0].path[:path_offset + 1]],
        )

    def _make_list_crown(self, leaf_to_path: PathedLeafs[LeafInpCrown], path_offset: int) -> InpListCrown:
        return InpListCrown(
            map=self._get_list_crown_map(leaf_to_path, path_offset),
            extra_policy=cast(ListExtraPolicy, self.extra_policies[leaf_to_path[0].path[:path_offset]]),
        )


class OutCrownBuilder(BaseCrownBuilder[LeafOutCrown, OutDictCrown, OutListCrown]):
    def __init__(self, path_to_sieves: PathsTo[Sieve]):
        self.path_to_sieves = path_to_sieves

    def _make_dict_crown(self, leaf_to_path: PathedLeafs[LeafOutCrown], path_offset: int) -> OutDictCrown:
        key_to_sieve: Dict[str, Sieve] = {}
        for leaf_with_path in leaf_to_path:
            sieve = self.path_to_sieves.get(leaf_with_path.path[:path_offset + 1])
            if sieve is not None:
                key_to_sieve[cast(str, leaf_with_path.path[path_offset])] = sieve

        return OutDictCrown(
            map=self._get_dict_crown_map(leaf_to_path, path_offset),
            sieves=key_to_sieve,
        )

    def _make_list_crown(self, leaf_to_path: PathedLeafs[LeafOutCrown], path_offset: int) -> OutListCrown:
        return OutListCrown(
            map=self._get_list_crown_map(leaf_to_path, path_offset),
        )
