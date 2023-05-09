from collections import defaultdict
from dataclasses import dataclass
from typing import (
    AbstractSet,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from ...common import EllipsisType, VarTuple
from ...model_tools import BaseField, DefaultFactory, DefaultValue, InputField, NoDefault, OutputField
from ...utils import Omittable
from ..essential import CannotProvide, Mediator
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
    InpNoneCrown,
    InputNameLayoutRequest,
    LeafBaseCrown,
    LeafInpCrown,
    LeafOutCrown,
    OutExtraMove,
    OutFieldCrown,
    OutNoneCrown,
    OutputNameLayoutRequest,
)
from ..model.fields import field_to_loc_map
from ..model.special_cases_optimization import with_default_clause
from ..name_style import NameStyle, convert_snake_style
from ..overlay_schema import Overlay, Schema, provide_schema
from ..request_cls import FieldLoc, LocatedRequest, TypeHintLoc
from ..request_filtering import ExtraStackMediator, NameMappingRuleRequest, RequestChecker
from .base import ExtraIn, ExtraMoveMaker, ExtraOut, ExtraPoliciesMaker, Key, Path, PathsTo, SievesMaker, StructureMaker

RawKey = Union[Key, EllipsisType]
RawPath = VarTuple[RawKey]
NameMapStack = VarTuple[Tuple[Pattern, RawPath]]


@dataclass
class StructureSchema(Schema):
    skip: RequestChecker
    only: RequestChecker

    map: NameMapStack
    trim_trailing_underscore: bool
    name_style: Optional[NameStyle]


@dataclass
class StructureOverlay(Overlay[StructureSchema]):
    skip: Omittable[RequestChecker]
    only: Omittable[RequestChecker]

    map: Omittable[NameMapStack]
    trim_trailing_underscore: Omittable[bool]
    name_style: Omittable[Optional[NameStyle]]

    def _merge_map(self, old: NameMapStack, new: NameMapStack) -> NameMapStack:
        return new + old


F = TypeVar('F', bound=BaseField)
AnyField = Union[InputField, OutputField]
LeafCr = TypeVar('LeafCr', bound=LeafBaseCrown)


def location_to_string(request: LocatedRequest) -> str:
    loc_map = request.loc_map
    if loc_map.has(TypeHintLoc, FieldLoc):
        return f' at type {loc_map[TypeHintLoc].type} that situated at field {request.loc_map[FieldLoc].name!r}'
    if loc_map.has(TypeHintLoc):
        return f' at type {loc_map[TypeHintLoc].type}'
    if loc_map.has(FieldLoc):
        return f' situated at field {request.loc_map[FieldLoc].name!r}'
    return ''


def apply_rc(mediator: Mediator, request_checker: RequestChecker, field: BaseField, is_mapped: bool) -> bool:
    request = NameMappingRuleRequest(loc_map=field_to_loc_map(field), is_mapped=is_mapped)
    try:
        request_checker.check_request(
            ExtraStackMediator(mediator, [request]),
            request,
        )
    except CannotProvide:
        return False
    return True


class BuiltinStructureMaker(StructureMaker):
    def _ensure_field_path(self, schema: StructureSchema, field: BaseField) -> Tuple[Path, bool]:
        name = field.id
        for pattern, raw_path in schema.map:
            if pattern.fullmatch(field.id):
                path = tuple(
                    field.id if isinstance(el, EllipsisType) else el
                    for el in raw_path
                )
                return path, True

        if schema.trim_trailing_underscore and name.endswith('_') and not name.endswith('__'):
            name = name.rstrip('_')
        if schema.name_style is not None:
            name = convert_snake_style(name, schema.name_style)
        return (name, ), False

    def _fields_to_paths(
        self,
        mediator: Mediator,
        schema: StructureSchema,
        fields: Iterable[F],
        extra_move: Union[InpExtraMove, OutExtraMove],
    ) -> Iterable[Tuple[F, Optional[Path], bool]]:
        if isinstance(extra_move, ExtraTargets):
            extra_targets = extra_move.fields
        else:
            extra_targets = ()

        for field in fields:
            if field.id in extra_targets:
                continue

            path, is_mapped = self._ensure_field_path(schema, field)
            if (
                not apply_rc(mediator, schema.skip, field, is_mapped)
                and apply_rc(mediator, schema.only, field, is_mapped)
            ):
                yield field, path, is_mapped
            else:
                yield field, None, is_mapped

    def _validate_structure(
        self,
        request: LocatedRequest,
        fields_to_paths: Iterable[Tuple[AnyField, Optional[Path], bool]],
    ) -> None:
        paths_to_fields: DefaultDict[Path, List[AnyField]] = defaultdict(list)
        for field, path, _is_mapped in fields_to_paths:
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
            for field, path, is_mapped in fields_to_paths
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

    def _fill_gaps_at_list(
        self,
        gaps_filler: Callable[[Path], LeafCr],
        request: LocatedRequest,
        paths_to_leaves: MutableMapping[Path, LeafCr],
    ) -> None:
        paths_to_lists = self._get_paths_to_list(request, paths_to_leaves.keys())
        for path, indexes in paths_to_lists.items():
            for i in range(max(indexes)):
                if i not in indexes:
                    complete_path = path + (i, )
                    paths_to_leaves[complete_path] = gaps_filler(complete_path)

    def _fill_input_gap(self, path: Path) -> LeafInpCrown:
        return InpNoneCrown()

    def _fill_output_gap(self, path: Path) -> LeafOutCrown:
        return OutNoneCrown(filler=DefaultValue(None))

    def make_inp_structure(
        self,
        mediator: Mediator,
        request: InputNameLayoutRequest,
        extra_move: InpExtraMove,
    ) -> Tuple[PathsTo[LeafInpCrown], AbstractSet[str]]:
        schema = provide_schema(StructureOverlay, mediator, request.loc_map)
        fields_to_paths = list(self._fields_to_paths(mediator, schema, request.figure.fields, extra_move))
        skipped_required_fields = [
            field.id
            for field, path, is_mapped in fields_to_paths
            if path is None and field.is_required
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped" + location_to_string(request)
            )
        self._validate_structure(request, fields_to_paths)
        paths_to_leaves: Dict[Path, LeafInpCrown] = {
            path: InpFieldCrown(field.id)
            for field, path, is_mapped in fields_to_paths
            if path is not None
        }
        self._fill_gaps_at_list(self._fill_input_gap, request, paths_to_leaves)
        mapped_fields = {field.id for field, path, is_mapped in fields_to_paths if is_mapped}
        return paths_to_leaves, mapped_fields

    def make_out_structure(
        self,
        mediator: Mediator,
        request: OutputNameLayoutRequest,
        extra_move: OutExtraMove,
    ) -> Tuple[PathsTo[LeafOutCrown], AbstractSet[str]]:
        schema = provide_schema(StructureOverlay, mediator, request.loc_map)
        fields_to_paths = list(self._fields_to_paths(mediator, schema, request.figure.fields, extra_move))
        self._validate_structure(request, fields_to_paths)
        paths_to_leaves: Dict[Path, LeafOutCrown] = {
            path: OutFieldCrown(field.id)
            for field, path, is_mapped in fields_to_paths
            if path is not None
        }
        self._fill_gaps_at_list(self._fill_output_gap, request, paths_to_leaves)
        mapped_fields = {field.id for field, path, is_mapped in fields_to_paths if is_mapped}
        return paths_to_leaves, mapped_fields


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
        mapped_fields: AbstractSet[str],
    ) -> PathsTo[Sieve]:
        schema = provide_schema(SievesOverlay, mediator, request.loc_map)
        result = {}
        for path, leaf in paths_to_leaves.items():
            if isinstance(leaf, OutFieldCrown):
                field = request.figure.fields_dict[leaf.name]
                is_mapped = field.id in mapped_fields
                if field.default != NoDefault() and apply_rc(mediator, schema.omit_default, field, is_mapped):
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
        mapped_fields: AbstractSet[str],
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
