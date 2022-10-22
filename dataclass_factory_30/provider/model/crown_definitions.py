from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, List, Mapping, MutableMapping, TypeVar, Union

from ...common import VarTuple
from ...model_tools import BaseFigure, DefaultFactory, DefaultValue, InputFigure, OutputFigure
from ...utils import SingletonMeta
from ..essential import Mediator
from ..request_cls import TypeHintRM
from ..static_provider import StaticProvider, static_provision_action

T = TypeVar('T')

CrownPathElem = Union[str, int]
CrownPath = VarTuple[CrownPathElem]  # subset of struct_path.Path


# Policies how to process extra data

class ExtraSkip(metaclass=SingletonMeta):
    """Ignore any extra data"""


class ExtraForbid(metaclass=SingletonMeta):
    """Raise error if extra data would be met"""


class ExtraCollect(metaclass=SingletonMeta):
    """Collect extra data and pass it to object"""


# --------  Base classes for crown -------- #

# Crown defines mapping of fields to structure of lists and dicts
# as well as the policy of extra data processing.
# This structure is named in honor of the crown of the tree.
#
# NoneCrown-s represent element that do not map to any field


@dataclass(frozen=True)
class BaseDictCrown(Generic[T]):
    map: Dict[str, T]


@dataclass(frozen=True)
class BaseListCrown(Generic[T]):
    map: List[T]


@dataclass(frozen=True)
class BaseNoneCrown:
    pass


@dataclass(frozen=True)
class BaseFieldCrown:
    name: str


BaseCrown = Union[BaseDictCrown, BaseListCrown, BaseNoneCrown, BaseFieldCrown]
RootBaseCrown = Union[BaseDictCrown, BaseListCrown]

# --------  Input Crown -------- #

DictExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]
ListExtraPolicy = Union[ExtraSkip, ExtraForbid]


@dataclass(frozen=True)
class InpDictCrown(BaseDictCrown['InpCrown']):
    extra_policy: DictExtraPolicy


@dataclass(frozen=True)
class InpListCrown(BaseListCrown['InpCrown']):
    extra_policy: ListExtraPolicy


@dataclass(frozen=True)
class InpNoneCrown(BaseNoneCrown):
    pass


@dataclass(frozen=True)
class InpFieldCrown(BaseFieldCrown):
    pass


InpCrown = Union[InpDictCrown, InpListCrown, InpFieldCrown, InpNoneCrown]
RootInpCrown = Union[InpDictCrown, InpListCrown]

# --------  Output Crown -------- #

# Sieve takes raw field value and determines if skip field.
# True indicates to put field, False to skip.
Sieve = Callable[[Any], bool]


@dataclass(frozen=True)
class OutDictCrown(BaseDictCrown['OutCrown']):
    sieves: Dict[str, Sieve]

    def _validate(self):
        wild_sieves = self.sieves.keys() - self.map.keys()
        if wild_sieves:
            raise ValueError(
                f"Sieves {wild_sieves} are attached to non-existing keys"
            )

    def __post_init__(self):
        self._validate()


@dataclass(frozen=True)
class OutListCrown(BaseListCrown['OutCrown']):
    pass


Filler = Union[DefaultValue, DefaultFactory]


@dataclass(frozen=True)
class OutNoneCrown(BaseNoneCrown):
    filler: Filler


@dataclass(frozen=True)
class OutFieldCrown(BaseFieldCrown):
    pass


OutCrown = Union[OutDictCrown, OutListCrown, OutNoneCrown, OutFieldCrown]
RootOutCrown = Union[OutDictCrown, OutListCrown]

# --------  Name Mapping -------- #


class ExtraKwargs(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class ExtraTargets:
    fields: VarTuple[str]


Saturator = Callable[[T, MutableMapping[str, Any]], None]
Extractor = Callable[[T], Mapping[str, Any]]


@dataclass(frozen=True)
class ExtraSaturate(Generic[T]):
    func: Saturator[T]


@dataclass(frozen=True)
class ExtraExtract(Generic[T]):
    func: Extractor[T]


InpExtraMove = Union[None, ExtraTargets, ExtraKwargs, ExtraSaturate[T]]
OutExtraMove = Union[None, ExtraTargets, ExtraExtract[T]]
BaseExtraMove = Union[InpExtraMove, OutExtraMove]


@dataclass(frozen=True)
class BaseNameMapping:
    crown: RootBaseCrown
    extra_move: BaseExtraMove


@dataclass(frozen=True)
class BaseNameMappingRequest(TypeHintRM[T], Generic[T]):
    figure: BaseFigure


@dataclass(frozen=True)
class InputNameMapping(BaseNameMapping):
    crown: RootInpCrown
    extra_move: InpExtraMove


@dataclass(frozen=True)
class InputNameMappingRequest(BaseNameMappingRequest[InputNameMapping]):
    figure: InputFigure


@dataclass(frozen=True)
class OutputNameMapping(BaseNameMapping):
    crown: RootOutCrown
    extra_move: OutExtraMove


@dataclass(frozen=True)
class OutputNameMappingRequest(BaseNameMappingRequest[OutputNameMapping]):
    figure: OutputFigure


class NameMappingProvider(StaticProvider, ABC):
    @abstractmethod
    @static_provision_action
    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> InputNameMapping:
        ...

    @abstractmethod
    @static_provision_action
    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> OutputNameMapping:
        ...
