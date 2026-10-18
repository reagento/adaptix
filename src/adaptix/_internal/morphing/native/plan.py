from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from typing import Any, ClassVar

from adaptix._internal.common import Dumper, Loader
from adaptix._internal.definitions import DebugTrail
from adaptix._internal.model_tools.definitions import InputShape, OutputShape
from adaptix._internal.morphing.model.crown_definitions import InputNameLayout, OutputNameLayout
from adaptix._internal.morphing.model.loader_gen import ModelLoaderProps


@dataclass(frozen=True, kw_only=True)
class ScalarPlan:
    mapper: Loader | Dumper
    name: ClassVar[str] = "native_scalar_mapper"

    @property
    def fallback(self) -> Loader | Dumper:
        return self.mapper


@dataclass(frozen=True, kw_only=True)
class IterablePlan:
    origin: Any
    mapper: Loader | Dumper
    fallback: Loader | Dumper
    debug_trail: DebugTrail
    loading: bool
    strict_coercion: bool
    dump_as: Any = list

    @property
    def name(self) -> str:
        container = "set" if self.origin in (set, frozenset) else "list"
        return f"native_{container}_{'loader' if self.loading else 'dumper'}"


@dataclass(frozen=True, kw_only=True)
class TuplePlan:
    mappers: Sequence[Loader | Dumper]
    fallback: Loader | Dumper
    snapshot_fallback: Loader | Dumper
    loading: bool
    strict_coercion: bool
    debug_trail: DebugTrail

    @property
    def name(self) -> str:
        return "native_tuple_loader" if self.loading else "native_tuple_dumper"


@dataclass(frozen=True, kw_only=True)
class DictPlan:
    key_mapper: Loader | Dumper
    value_mapper: Loader | Dumper
    fallback: Loader | Dumper
    loading: bool
    debug_trail: DebugTrail

    @property
    def name(self) -> str:
        return "native_dict_loader" if self.loading else "native_dict_dumper"


@dataclass(frozen=True, kw_only=True)
class UnionPlan:
    loaders: Sequence[Loader]
    fallback: Loader
    tp: Any
    debug_trail: DebugTrail
    name: ClassVar[str] = "native_tagged_union_loader"


@dataclass(frozen=True, kw_only=True)
class ModelPlan:
    name: str
    debug_trail: DebugTrail
    model_identity: str


@dataclass(frozen=True, kw_only=True)
class ModelLoaderPlan(ModelPlan):
    shape: InputShape
    name_layout: InputNameLayout
    strict_coercion: bool
    field_loaders: Mapping[str, Loader]
    skipped_fields: Set[str]
    props: ModelLoaderProps


@dataclass(frozen=True, kw_only=True)
class ModelDumperPlan(ModelPlan):
    shape: OutputShape
    name_layout: OutputNameLayout
    fields_dumpers: Mapping[str, Dumper]


NativePlan = ScalarPlan | IterablePlan | TuplePlan | DictPlan | UnionPlan | ModelLoaderPlan | ModelDumperPlan
