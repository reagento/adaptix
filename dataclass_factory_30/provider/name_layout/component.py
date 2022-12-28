from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Pattern, Sequence, Set, Tuple, Union

from ...common import EllipsisType, VarTuple
from ...model_tools import BaseField, DefaultFactory, DefaultValue, OutputField
from ...utils import Omittable
from ..essential import Mediator
from ..model import Sieve
from ..model.crown_definitions import (
    DictExtraPolicy,
    ExtraCollect,
    ExtraExtract,
    ExtraForbid,
    ExtraKwargs,
    ExtraSaturate,
    ExtraSkip,
    ExtraTargets,
    InpExtraMove,
    InpFieldCrown,
    InputNameLayoutRequest,
    LeafBaseCrown,
    LeafInpCrown,
    LeafOutCrown,
    OutExtraMove,
    OutFieldCrown,
    OutputNameLayoutRequest,
)
from ..name_style import NameStyle, convert_snake_style
from ..overlay import Overlay, Schema, provide_schema
from .base import ExtraIn, ExtraMoveMaker, ExtraOut, ExtraPoliciesMaker, Key, Path, PathsTo, SievesMaker, StructureMaker

RawKey = Union[Key, EllipsisType]
NameMap = Mapping[str, Iterable[RawKey]]

RawPath = VarTuple[RawKey]
NameMapStack = VarTuple[Tuple[Pattern, RawPath]]


@dataclass
class StructureSchema(Schema):
    skip: Iterable[str]
    only_mapped: bool
    only: Optional[Iterable[str]]

    map: NameMapStack
    trim_trailing_underscore: bool
    name_style: Optional[NameStyle]


@dataclass
class StructureOverlay(Overlay[StructureSchema]):
    skip: Omittable[Iterable[str]]
    only_mapped: Omittable[bool]
    only: Omittable[Optional[Iterable[str]]]

    map: Omittable[NameMapStack]
    trim_trailing_underscore: Omittable[bool]
    name_style: Omittable[Optional[NameStyle]]

    def _merge_map(self, old: NameMapStack, new: NameMapStack) -> NameMapStack:
        return new + old


class BuiltinStructureMaker(StructureMaker):
    def _map_name(self, schema: StructureSchema, field: BaseField) -> Tuple[Path, bool]:
        name = field.name
        for pattern, raw_path in schema.map:
            if pattern.fullmatch(field.name):
                return tuple(field.name if isinstance(el, EllipsisType) else el for el in raw_path), True

        if schema.trim_trailing_underscore:
            name = name.rstrip('_')
        if schema.name_style is not None:
            name = convert_snake_style(name, schema.name_style)
        return (name,), False

    def _fields_to_paths(self, schema: StructureSchema, fields: Iterable[BaseField]) -> Iterable[Tuple[Path, str]]:
        filtered_fields = [field for field in fields if field.name not in schema.skip]
        for field in filtered_fields:
            path, is_mapped = self._map_name(schema, field)
            if (
                (schema.only is not None and field.name in schema.only)
                or (schema.only_mapped and is_mapped)
            ):
                yield path, field.name

    def make_inp_structure(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
    ) -> PathsTo[LeafInpCrown]:
        schema = provide_schema(StructureOverlay, mediator, request.loc)
        return {
            path: InpFieldCrown(name)
            for path, name in self._fields_to_paths(schema, request.figure.fields)
        }

    def make_out_structure(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
    ) -> PathsTo[LeafOutCrown]:
        schema = provide_schema(StructureOverlay, mediator, request.loc)
        return {
            path: OutFieldCrown(name)
            for path, name in self._fields_to_paths(schema, request.figure.fields)
        }


@dataclass
class SievesSchema(Schema):
    omit_default: bool


@dataclass
class SievesOverlay(Overlay[SievesSchema]):
    omit_default: Omittable[bool]


class BuiltinSievesMaker(SievesMaker):
    def _create_sieve(self, field: OutputField) -> Sieve:
        if isinstance(field.default, DefaultValue):
            default_value = field.default.value

            return lambda x: x != default_value

        if isinstance(field.default, DefaultFactory):
            default_factory = field.default.factory

            return lambda x: x != default_factory()

        raise ValueError

    def make_sieves(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafOutCrown],
    ) -> PathsTo[Sieve]:
        schema = provide_schema(SievesOverlay, mediator, request.loc)
        if schema.omit_default:
            return {
                path: self._create_sieve(request.figure.fields_dict[leaf.name])
                for path, leaf in path_to_leaf.items()
                if isinstance(leaf, OutFieldCrown)
            }
        return {}


def paths_to_branches(path_to_leaf: PathsTo[LeafBaseCrown]) -> Iterable[Path]:
    yielded: Set[Path] = set()
    for path in path_to_leaf.keys():
        for i in range(len(path) - 1, 1, -1):
            sub_path = path[:i]
            if sub_path in yielded:
                break

            yield sub_path


@dataclass
class ExtraMoveAndPoliciesSchema(Schema):
    extra_in: ExtraIn
    extra_out: ExtraOut


@dataclass
class ExtraMoveAndPoliciesOverlay(Overlay[ExtraMoveAndPoliciesSchema]):
    extra_in: Omittable[ExtraIn]
    extra_out: Omittable[ExtraOut]


class BuiltinExtraMoveAndPoliciesMaker(ExtraMoveMaker, ExtraPoliciesMaker):
    def _create_extra_targets(self, extra: Union[str, Sequence[str]]) -> ExtraTargets:
        if isinstance(extra, str):
            return ExtraTargets((extra,))
        return ExtraTargets(tuple(extra))

    def make_inp_extra_move(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafInpCrown],
    ) -> InpExtraMove:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc)
        if schema.extra_in in (ExtraForbid(), ExtraSkip()):
            return None
        if schema.extra_in == ExtraKwargs():
            return ExtraKwargs()
        if callable(schema.extra_in):
            return ExtraSaturate(schema.extra_in)
        return self._create_extra_targets(schema.extra_in)  # type: ignore[arg-type]

    def make_out_extra_move(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafOutCrown],
    ) -> OutExtraMove:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc)
        if schema.extra_out == ExtraSkip():
            return None
        if callable(schema.extra_out):
            return ExtraExtract(schema.extra_out)
        return self._create_extra_targets(schema.extra_out)  # type: ignore[arg-type]

    def _get_extra_policy(self, schema: ExtraMoveAndPoliciesSchema) -> DictExtraPolicy:
        if schema.extra_in == ExtraSkip():
            return ExtraSkip()
        if schema.extra_in == ExtraForbid():
            return ExtraForbid()
        return ExtraCollect()

    def make_extra_policies(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        path_to_leaf: PathsTo[LeafInpCrown],
    ) -> PathsTo[DictExtraPolicy]:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc)
        policy = self._get_extra_policy(schema)
        path_to_extra_policy: Dict[Path, DictExtraPolicy] = {}
        for path in paths_to_branches(path_to_leaf):
            if policy == ExtraCollect() and isinstance(path[-1], int):
                raise ValueError("Can not collect data from list")
            path_to_extra_policy[path] = policy
        return path_to_extra_policy
