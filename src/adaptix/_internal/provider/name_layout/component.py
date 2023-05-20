from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, TypeVar, Union

from ...common import VarTuple
from ...essential import CannotProvide, Mediator, Provider
from ...model_tools.definitions import BaseField, DefaultFactory, DefaultValue, InputField, NoDefault, OutputField
from ...retort.operating_retort import OperatingRetort
from ...utils import Omittable
from ..model.crown_definitions import (
    BaseFieldCrown,
    BaseNameLayoutRequest,
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
    InpNoneCrown,
    InputNameLayoutRequest,
    LeafBaseCrown,
    LeafInpCrown,
    LeafOutCrown,
    OutExtraMove,
    OutFieldCrown,
    OutNoneCrown,
    OutputNameLayoutRequest,
    Sieve,
)
from ..model.fields import field_to_loc_map
from ..model.special_cases_optimization import with_default_clause
from ..name_style import NameStyle, convert_snake_style
from ..overlay_schema import Overlay, Schema, provide_schema
from ..request_cls import FieldLoc, LocatedRequest, TypeHintLoc
from ..request_filtering import ExtraStackMediator, RequestChecker
from .base import ExtraIn, ExtraMoveMaker, ExtraOut, ExtraPoliciesMaker, Key, Path, PathsTo, SievesMaker, StructureMaker
from .name_mapping import NameMappingFilterRequest, NameMappingRequest


@dataclass
class StructureSchema(Schema):
    skip: RequestChecker
    only: RequestChecker

    map: VarTuple[Provider]
    trim_trailing_underscore: bool
    name_style: Optional[NameStyle]


@dataclass
class StructureOverlay(Overlay[StructureSchema]):
    skip: Omittable[RequestChecker]
    only: Omittable[RequestChecker]

    map: Omittable[VarTuple[Provider]]
    trim_trailing_underscore: Omittable[bool]
    name_style: Omittable[Optional[NameStyle]]

    def _merge_map(self, old: VarTuple[Provider], new: VarTuple[Provider]) -> VarTuple[Provider]:
        return new + old


AnyField = Union[InputField, OutputField]
LeafCr = TypeVar('LeafCr', bound=LeafBaseCrown)
FieldCr = TypeVar('FieldCr', bound=BaseFieldCrown)
F = TypeVar('F', bound=BaseField)
FieldAndPath = Tuple[F, Optional[Path]]


def location_to_string(request: LocatedRequest) -> str:
    loc_map = request.loc_map
    if loc_map.has(TypeHintLoc, FieldLoc):
        return f' at type {loc_map[TypeHintLoc].type} that situated at field {request.loc_map[FieldLoc].name!r}'
    if loc_map.has(TypeHintLoc):
        return f' at type {loc_map[TypeHintLoc].type}'
    if loc_map.has(FieldLoc):
        return f' situated at field {request.loc_map[FieldLoc].name!r}'
    return ''


def apply_rc(mediator: Mediator, request_checker: RequestChecker, field: BaseField) -> bool:
    request = NameMappingFilterRequest(loc_map=field_to_loc_map(field))
    try:
        request_checker.check_request(
            ExtraStackMediator(mediator, [request]),
            request,
        )
    except CannotProvide:
        return False
    return True


class BuiltinStructureMaker(StructureMaker):
    def _make_non_mapped_path(self, schema: StructureSchema, field: BaseField) -> Optional[Path]:
        name = field.id
        if schema.trim_trailing_underscore and name.endswith('_') and not name.endswith('__'):
            name = name.rstrip('_')
        if schema.name_style is not None:
            name = convert_snake_style(name, schema.name_style)
        return (name, )

    def _create_map_provider(self, schema: StructureSchema) -> Provider:
        return OperatingRetort(recipe=schema.map)

    def _map_fields(
        self,
        mediator: Mediator,
        request: BaseNameLayoutRequest,
        schema: StructureSchema,
        extra_move: Union[InpExtraMove, OutExtraMove],
    ) -> Iterable[FieldAndPath]:
        extra_targets = extra_move.fields if isinstance(extra_move, ExtraTargets) else ()
        map_provider = self._create_map_provider(schema)
        for field in request.shape.fields:
            if field.id in extra_targets:
                continue

            try:
                path = map_provider.apply_provider(
                    mediator,
                    NameMappingRequest(
                        shape=request.shape,
                        field=field,
                        loc_map=field_to_loc_map(field),
                    )
                )
            except CannotProvide:
                path = self._make_non_mapped_path(schema, field)

            if path is None:
                yield field, None
            elif (
                not apply_rc(mediator, schema.skip, field)
                and apply_rc(mediator, schema.only, field)
            ):
                yield field, path
            else:
                yield field, None

    def _validate_structure(
        self,
        request: LocatedRequest,
        fields_to_paths: Iterable[FieldAndPath],
    ) -> None:
        paths_to_fields: DefaultDict[Path, List[AnyField]] = defaultdict(list)
        for field, path in fields_to_paths:
            if path is not None:
                paths_to_fields[path].append(field)

        duplicates = {
            path: [field.id for field in fields]
            for path, fields in paths_to_fields.items()
            if len(fields) > 1
        }
        if duplicates:
            raise ValueError(
                f"Paths {duplicates} pointed to several fields" + location_to_string(request)
            )

        optional_fields_at_list = [
            field.id
            for field, path in fields_to_paths
            if path is not None and field.is_optional and isinstance(path[-1], int)
        ]
        if optional_fields_at_list:
            raise ValueError(
                f"Optional fields {optional_fields_at_list} can not be mapped to list elements"
                + location_to_string(request)
            )

    def _iterate_sub_paths(self, paths: Iterable[Path]) -> Iterable[Tuple[Path, Key]]:
        yielded: Set[Tuple[Path, Key]] = set()
        for path in paths:
            for i in range(len(path) - 1, -1, -1):
                result = path[:i], path[i]
                if result in yielded:
                    break

                yielded.add(result)
                yield result

    def _get_paths_to_list(self, request: LocatedRequest, paths: Iterable[Path]) -> Mapping[Path, Set[int]]:
        paths_to_lists: DefaultDict[Path, Set[int]] = defaultdict(set)
        paths_to_dicts: Set[Path] = set()
        for sub_path, key in self._iterate_sub_paths(paths):
            if isinstance(key, int):
                if sub_path in paths_to_dicts:
                    raise ValueError(
                        f"Inconsistent path elements at {sub_path}" + location_to_string(request)
                    )

                paths_to_lists[sub_path].add(key)
            else:
                if sub_path in paths_to_lists:
                    raise ValueError(
                        f"Inconsistent path elements at {sub_path}" + location_to_string(request)
                    )

                paths_to_dicts.add(sub_path)

        return paths_to_lists

    def _make_paths_to_leaves(
        self,
        request: LocatedRequest,
        fields_to_paths: Iterable[FieldAndPath],
        field_crown: Callable[[str], FieldCr],
        gaps_filler: Callable[[Path], LeafCr],
    ) -> PathsTo[Union[FieldCr, LeafCr]]:
        paths_to_leaves: Dict[Path, Union[FieldCr, LeafCr]] = {
            path: field_crown(field.id)
            for field, path in fields_to_paths
            if path is not None
        }

        paths_to_lists = self._get_paths_to_list(request, paths_to_leaves.keys())
        for path, indexes in paths_to_lists.items():
            for i in range(max(indexes)):
                if i not in indexes:
                    complete_path = path + (i, )
                    paths_to_leaves[complete_path] = gaps_filler(complete_path)

        return paths_to_leaves

    def _fill_input_gap(self, path: Path) -> LeafInpCrown:
        return InpNoneCrown()

    def _fill_output_gap(self, path: Path) -> LeafOutCrown:
        return OutNoneCrown(filler=DefaultValue(None))

    def make_inp_structure(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        extra_move: InpExtraMove,
    ) -> PathsTo[LeafInpCrown]:
        schema = provide_schema(StructureOverlay, mediator, request.loc_map)
        fields_to_paths: List[FieldAndPath[InputField]] = list(
            self._map_fields(mediator, request, schema, extra_move)
        )
        skipped_required_fields = [
            field.id
            for field, path in fields_to_paths
            if path is None and field.is_required
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped" + location_to_string(request)
            )
        self._validate_structure(request, fields_to_paths)
        return self._make_paths_to_leaves(request, fields_to_paths, InpFieldCrown, self._fill_input_gap)

    def make_out_structure(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        extra_move: OutExtraMove,
    ) -> PathsTo[LeafOutCrown]:
        schema = provide_schema(StructureOverlay, mediator, request.loc_map)
        fields_to_paths: List[FieldAndPath[OutputField]] = list(
            self._map_fields(mediator, request, schema, extra_move)
        )
        self._validate_structure(request, fields_to_paths)
        return self._make_paths_to_leaves(request, fields_to_paths, OutFieldCrown, self._fill_output_gap)


@dataclass
class SievesSchema(Schema):
    omit_default: RequestChecker


@dataclass
class SievesOverlay(Overlay[SievesSchema]):
    omit_default: Omittable[RequestChecker]


class BuiltinSievesMaker(SievesMaker):
    def _create_sieve(self, field: OutputField) -> Sieve:
        if isinstance(field.default, DefaultValue):
            default_value = field.default.value
            return with_default_clause(lambda x: x != default_value, field.default)

        if isinstance(field.default, DefaultFactory):
            default_factory = field.default.factory
            return with_default_clause(lambda x: x != default_factory(), field.default)

        raise ValueError

    def make_sieves(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        paths_to_leaves: PathsTo[LeafOutCrown],
    ) -> PathsTo[Sieve]:
        schema = provide_schema(SievesOverlay, mediator, request.loc_map)
        result = {}
        for path, leaf in paths_to_leaves.items():
            if isinstance(leaf, OutFieldCrown):
                field = request.shape.fields_dict[leaf.id]
                if field.default != NoDefault() and apply_rc(mediator, schema.omit_default, field):
                    result[path] = self._create_sieve(field)
        return result


def _paths_to_branches(paths_to_leaves: PathsTo[LeafBaseCrown]) -> Iterable[Tuple[Path, Key]]:
    yielded_branch_path: Set[Path] = set()
    for path in paths_to_leaves.keys():
        for i in range(len(path) - 1, -2, -1):
            sub_path = path[:i]
            if sub_path in yielded_branch_path:
                break

            yield sub_path, path[i]


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
    ) -> InpExtraMove:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc_map)
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
    ) -> OutExtraMove:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc_map)
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
        paths_to_leaves: PathsTo[LeafInpCrown],
    ) -> PathsTo[DictExtraPolicy]:
        schema = provide_schema(ExtraMoveAndPoliciesOverlay, mediator, request.loc_map)
        policy = self._get_extra_policy(schema)
        path_to_extra_policy: Dict[Path, DictExtraPolicy] = {
            (): policy,
        }
        for path, key in _paths_to_branches(paths_to_leaves):
            if policy == ExtraCollect() and isinstance(key, int):
                raise ValueError("Can not use collecting extra_in with list mapping" + location_to_string(request))
            path_to_extra_policy[path] = policy
        return path_to_extra_policy
