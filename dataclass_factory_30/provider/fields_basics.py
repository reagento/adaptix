"""This module contains essential concepts of fields.

Crown defines how external structure
should be mapped to constructor fields
and defines the policy of extra data processing.

None means that item of dict or list maps to nothing.

This structure is named in honor of the crown of the tree.

For example,
DictCrown(
    {
        'a': FieldCrown('x'),
        'b': ListCrown(
            {
                0: FieldCrown('y'),
                1: FieldCrown('z'),
                2: None,
            },
            extra=ExtraForbid(),
        ),
    },
    extra=ExtraCollect(),
)
means that:
    x = data['a']
    y = data['b'][0]
    z = data['b'][1]

    List at data['b'] can have only 3 elements
    and value of element with index 2 is ignored.

    Dict `data` can contain additional keys
    that will be collected and passed to constructor
    according to FigureExtra of Figure.

Gaps at ListCrown.map is filled with None, e.g.

ListCrown(
  {
      0: FieldCrown('a'),
      2: FieldCrown('b')
   },
   extra=...
)

is same as

ListCrown(
  {
      0: FieldCrown('a'),
      1: None,
      2: FieldCrown('b')
   },
   extra=...
)
"""
import itertools
from abc import abstractmethod, ABC
from dataclasses import dataclass, replace
from enum import Enum
from itertools import islice
from typing import Union, Generic, TypeVar, Dict, Callable, Tuple, Collection, Iterable, List, Set

from .essential import Request, Mediator
from .request_cls import FieldRM, TypeHintRM, InputFieldRM, ParamKind
from .static_provider import StaticProvider, static_provision_action
from ..utils import SingletonMeta

T = TypeVar('T')


class GetterKind(Enum):
    ATTR = 0
    ITEM = 1


class ExtraSkip(metaclass=SingletonMeta):
    pass


class ExtraForbid(metaclass=SingletonMeta):
    pass


class ExtraKwargs(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class ExtraTargets:
    fields: Tuple[str, ...]


class ExtraCollect(metaclass=SingletonMeta):
    pass


FigureExtra = Union[None, ExtraKwargs, ExtraTargets]

ExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]


class CfgExtraPolicy(Request[ExtraPolicy]):
    pass


@dataclass(frozen=True)
class BaseFieldsFigure:
    fields: Tuple[FieldRM, ...]


@dataclass(frozen=True)
class InputFieldsFigure(BaseFieldsFigure):
    """InputFieldsFigure is the signature of the class.
    `constructor` field contains a callable that produces an instance of the class.
    `fields` field contains the extended function signature of the constructor.

    `extra` field contains the way of collecting extra data (data that does not map to any field)
    None means that constructor can not take any extra data.
    ExtraKwargs means that all extra data could be passed as additional keyword parameters
    ExtraTargets means that all extra data could be passed to corresponding fields.

    This field defines how extra data will be collected
    but crown defines whether extra data should be collected
    """
    fields: Tuple[InputFieldRM, ...]
    extra: FigureExtra
    constructor: Callable

    def __post_init__(self):
        self._validate()

    def _validate(self):
        for past, current in zip(self.fields, islice(self.fields, 1, None)):
            if past.param_kind.value > current.param_kind.value:
                raise ValueError(
                    f"Inconsistent order of fields,"
                    f" {current.param_kind} must be after {past.param_kind}"
                )

            if (
                not past.is_required
                and current.is_required
                and current.param_kind != ParamKind.KW_ONLY
            ):
                raise ValueError(
                    f"All not required fields must be after required ones"
                    f" except {ParamKind.KW_ONLY} fields"
                )

        field_names = {fld.name for fld in self.fields}
        if len(field_names) != len(self.fields):
            duplicates = {
                fld.name for fld in self.fields
                if fld.name in field_names
            }
            raise ValueError(f"Field names {duplicates} are duplicated")

        if isinstance(self.extra, ExtraTargets):
            wild_targets = [
                target for target in self.extra.fields
                if target not in field_names
            ]

            if wild_targets:
                raise ValueError(
                    f"ExtraTargets {wild_targets} are attached to non-existing fields"
                )


@dataclass(frozen=True)
class OutputFieldsFigure(BaseFieldsFigure):
    getter_kind: GetterKind


@dataclass
class DictCrown:
    map: Dict[str, 'Crown']
    extra: ExtraPolicy


@dataclass
class ListCrown:
    map: Dict[int, 'Crown']
    extra: Union[ExtraSkip, ExtraForbid]

    @property
    def list_len(self):
        return max(self.map) + 1


@dataclass
class FieldCrown:
    name: str


Crown = Union[FieldCrown, None, DictCrown, ListCrown]


@dataclass
class NameMapping:
    crown: Union[DictCrown, ListCrown]
    skipped_extra_targets: Collection[str]


@dataclass(frozen=True)
class BaseFFRequest(TypeHintRM[T], Generic[T]):
    pass


@dataclass(frozen=True)
class InputFFRequest(BaseFFRequest[InputFieldsFigure]):
    pass


@dataclass(frozen=True)
class OutputFFRequest(BaseFFRequest[OutputFieldsFigure]):
    pass


@dataclass(frozen=True)
class BaseNameMappingRequest(TypeHintRM[NameMapping]):
    figure: BaseFieldsFigure


@dataclass(frozen=True)
class InputNameMappingRequest(BaseNameMappingRequest):
    figure: InputFieldsFigure


@dataclass(frozen=True)
class OutputNameMappingRequest(BaseNameMappingRequest):
    figure: OutputFieldsFigure


class NameMappingProvider(StaticProvider, ABC):
    @abstractmethod
    @static_provision_action(InputNameMappingRequest)
    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> NameMapping:
        pass

    @abstractmethod
    @static_provision_action(OutputNameMappingRequest)
    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> NameMapping:
        pass

    # This method declared only for IDE autocompletion
    def _provide_name_mapping(self, mediator: Mediator, request: BaseNameMappingRequest) -> NameMapping:
        pass


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


class FigureProcessor:
    """FigureProcessor takes InputFieldsFigure and NameMapping,
    produces new InputFieldsFigure discarding unused fields
    and validating NameMapping
    """

    def _inner_collect_used_fields(self, crown: Crown):
        if isinstance(crown, (DictCrown, ListCrown)):
            return _merge_iters(
                self._inner_collect_used_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, FieldCrown):
            return [crown.name]
        if crown is None:
            return []

    def _collect_used_fields(self, crown: Crown) -> Set[str]:
        lst = self._inner_collect_used_fields(crown)

        used_set = set()
        for f_name in lst:
            if f_name in used_set:
                raise ValueError(f"Field {f_name!r} is duplicated at crown")
            used_set.add(f_name)

        return used_set

    def _field_is_skipped(
        self,
        field: InputFieldRM,
        skipped_extra_targets: Collection[str],
        used_fields: Set[str],
        extra_targets: Set[str]
    ):
        f_name = field.name
        if f_name in extra_targets:
            return f_name in skipped_extra_targets
        else:
            return f_name not in used_fields

    def _validate_required_fields(
        self,
        figure: InputFieldsFigure,
        used_fields: Set[str],
        extra_targets: Set[str],
        name_mapping: NameMapping,
    ):
        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and self._field_is_skipped(
                field,
                skipped_extra_targets=name_mapping.skipped_extra_targets,
                used_fields=used_fields,
                extra_targets=extra_targets
            )
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} not presented at name_mapping crown"
            )

    def _get_extra_targets(self, figure: InputFieldsFigure, used_fields: Set[str]):
        if isinstance(figure.extra, ExtraTargets):
            extra_targets = set(figure.extra.fields)

            extra_targets_at_crown = used_fields & extra_targets
            if extra_targets_at_crown:
                raise ValueError(
                    f"Fields {extra_targets_at_crown} can not be extra target"
                    f" and be presented at name_mapping"
                )

            return extra_targets

        return set()

    def process_figure(self, figure: InputFieldsFigure, name_mapping: NameMapping) -> InputFieldsFigure:
        used_fields = self._collect_used_fields(name_mapping.crown)
        extra_targets = self._get_extra_targets(figure, used_fields)

        self._validate_required_fields(
            figure=figure,
            used_fields=used_fields,
            extra_targets=extra_targets,
            name_mapping=name_mapping,
        )

        filtered_extra_targets = extra_targets - set(name_mapping.skipped_extra_targets)
        extra = figure.extra

        if isinstance(extra, ExtraTargets):
            extra = ExtraTargets(tuple(filtered_extra_targets))

        # leave only fields that will be passed to constructor
        new_figure = replace(
            figure,
            fields=tuple(
                fld for fld in figure.fields
                if fld.name in used_fields or fld.name in filtered_extra_targets
            ),
            extra=extra,
        )

        return new_figure
