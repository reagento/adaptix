from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import groupby
from typing import Dict, Generic, Mapping, Sequence, TypeVar, Union, cast

from ..model.crown_definitions import (
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
from .base import Path, PathsTo

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
        if not path_to_leaf:
            return self._make_dict_crown(current_path=(), paths_with_leafs=[])

        paths_with_leafs = [PathWithLeaf(path, leaf) for path, leaf in path_to_leaf.items()]
        paths_with_leafs.sort(key=lambda x: x.path)
        return cast(Union[DictCr, ListCr], self._build_crown(paths_with_leafs, 0))

    def _build_crown(self, paths_with_leafs: PathedLeafs[LeafCr], path_offset: int) -> Union[LeafCr, DictCr, ListCr]:
        if not paths_with_leafs:
            raise ValueError

        try:
            first = paths_with_leafs[0].path[path_offset]
        except IndexError:
            if len(paths_with_leafs) != 1:
                raise ValueError
            return paths_with_leafs[0].leaf

        if isinstance(first, str):
            return self._make_dict_crown(paths_with_leafs[0].path[:path_offset], paths_with_leafs)
        if isinstance(first, int):
            return self._make_list_crown(paths_with_leafs[0].path[:path_offset], paths_with_leafs)
        raise RuntimeError

    def _get_dict_crown_map(
        self,
        current_path: Path,
        paths_with_leafs: PathedLeafs[LeafCr],
    ) -> Mapping[str, Union[LeafCr, DictCr, ListCr]]:
        return {
            cast(str, key): self._build_crown(list(path_group), len(current_path) + 1)
            for key, path_group in groupby(paths_with_leafs, lambda x: x.path[len(current_path)])
        }

    @abstractmethod
    def _make_dict_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafCr]) -> DictCr:
        ...

    def _get_list_crown_map(
        self,
        current_path: Path,
        paths_with_leafs: PathedLeafs[LeafCr],
    ) -> Sequence[Union[LeafCr, DictCr, ListCr]]:
        grouped_paths = [
            list(grouped_paths)
            for key, grouped_paths in groupby(paths_with_leafs, lambda x: x.path[len(current_path)])
        ]
        if len(grouped_paths) != cast(int, paths_with_leafs[-1].path[len(current_path)]) + 1:
            raise ValueError(f"Found gaps in list mapping at {current_path}")
        return [
            self._build_crown(path_group, len(current_path) + 1)
            for path_group in grouped_paths
        ]

    @abstractmethod
    def _make_list_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafCr]) -> ListCr:
        ...


class InpCrownBuilder(BaseCrownBuilder[LeafInpCrown, InpDictCrown, InpListCrown]):
    def __init__(self, extra_policies: PathsTo[DictExtraPolicy]):
        self.extra_policies = extra_policies

    def _make_dict_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafInpCrown]) -> InpDictCrown:
        return InpDictCrown(
            map=self._get_dict_crown_map(current_path, paths_with_leafs),
            extra_policy=self.extra_policies[current_path],
        )

    def _make_list_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafInpCrown]) -> InpListCrown:
        return InpListCrown(
            map=self._get_list_crown_map(current_path, paths_with_leafs),
            extra_policy=cast(ListExtraPolicy, self.extra_policies[current_path]),
        )


class OutCrownBuilder(BaseCrownBuilder[LeafOutCrown, OutDictCrown, OutListCrown]):
    def __init__(self, path_to_sieves: PathsTo[Sieve]):
        self.path_to_sieves = path_to_sieves

    def _make_dict_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafOutCrown]) -> OutDictCrown:
        key_to_sieve: Dict[str, Sieve] = {}
        for leaf_with_path in paths_with_leafs:
            sieve = self.path_to_sieves.get(leaf_with_path.path[:len(current_path) + 1])
            if sieve is not None:
                key_to_sieve[cast(str, leaf_with_path.path[len(current_path)])] = sieve

        return OutDictCrown(
            map=self._get_dict_crown_map(current_path, paths_with_leafs),
            sieves=key_to_sieve,
        )

    def _make_list_crown(self, current_path: Path, paths_with_leafs: PathedLeafs[LeafOutCrown]) -> OutListCrown:
        return OutListCrown(
            map=self._get_list_crown_map(current_path, paths_with_leafs),
        )
