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

from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from typing import List, Union, Generic, TypeVar, Dict, Callable, Tuple, Collection

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

        field_names = {fld.field_name for fld in self.fields}
        if len(field_names) != len(self.fields):
            duplicates = {
                fld.field_name for fld in self.fields
                if fld.field_name in field_names
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
