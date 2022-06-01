from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Dict, List, Union, Callable, Any, Set, Collection

from ..definitions import (
    DefaultValue, DefaultFactory,
)
from ..essential import Request, Mediator
from ..fields.definitions import BaseFigure, OutputFigure, InputFigure
from ..request_cls import TypeHintRM
from ..static_provider import StaticProvider, static_provision_action
from ...utils import SingletonMeta

T = TypeVar('T')

FldPathElem = Union[str, int]


# Policies how to process extra data

class ExtraSkip(metaclass=SingletonMeta):
    """Ignore any extra data"""


class ExtraForbid(metaclass=SingletonMeta):
    """Raise error if extra data would be met"""


class ExtraCollect(metaclass=SingletonMeta):
    """Collect extra data and pass it to constructor"""


# --------  Base classes for crown -------- #

@dataclass
class BaseDictCrown(Generic[T]):
    map: Dict[str, T]


@dataclass
class BaseListCrown(Generic[T]):
    map: List[T]

    @property
    def list_len(self):
        return len(self.map)


@dataclass
class BaseNoneCrown:
    pass


@dataclass
class BaseFieldCrown:
    name: str


BaseCrown = Union[BaseDictCrown, BaseListCrown, BaseNoneCrown, BaseFieldCrown]


@dataclass
class BaseNameMapping:
    crown: Union[BaseDictCrown, BaseListCrown]
    used_extra_targets: Set[str]


# --------  Input Crown -------- #

InpExtraPolicyDict = Union[ExtraSkip, ExtraForbid, ExtraCollect]
InpExtraPolicyList = Union[ExtraSkip, ExtraForbid]


@dataclass
class InpDictCrown(BaseDictCrown['InpCrown']):
    extra: InpExtraPolicyDict


@dataclass
class InpListCrown(BaseListCrown['InpCrown']):
    extra: InpExtraPolicyList


@dataclass
class InpNoneCrown(BaseNoneCrown):
    pass


@dataclass
class InpFieldCrown(BaseFieldCrown):
    pass


InpCrown = Union[InpDictCrown, InpListCrown, InpFieldCrown, InpNoneCrown]
RootInpCrown = Union[InpDictCrown, InpListCrown]

# --------  Output Crown -------- #


Sieve = Callable[[Any], bool]


@dataclass
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


@dataclass
class OutListCrown(BaseListCrown['OutCrown']):
    pass


Filler = Union[DefaultValue, DefaultFactory]


@dataclass
class OutNoneCrown(BaseNoneCrown):
    filler: Filler


@dataclass
class OutFieldCrown(BaseFieldCrown):
    pass


OutCrown = Union[OutDictCrown, OutListCrown, OutNoneCrown, OutFieldCrown]
OutRootCrown = Union[OutDictCrown, OutListCrown]

# --------  Name Mapping -------- #

ExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]


class CfgExtraPolicy(Request[ExtraPolicy]):
    pass


@dataclass(frozen=True)
class BaseNameMapping:
    crown: Union[BaseDictCrown, BaseListCrown]
    skipped_extra_targets: Collection[str]


@dataclass(frozen=True)
class BaseNameMappingRequest(TypeHintRM[T], Generic[T]):
    figure: BaseFigure


@dataclass(frozen=True)
class InputNameMapping(BaseNameMapping):
    crown: Union[InpDictCrown, InpListCrown]


@dataclass(frozen=True)
class InputNameMappingRequest(BaseNameMappingRequest[InputNameMapping]):
    figure: InputFigure


@dataclass(frozen=True)
class OutputNameMapping(BaseNameMapping):
    crown: Union[OutDictCrown, OutListCrown]


@dataclass(frozen=True)
class OutputNameMappingRequest(BaseNameMappingRequest[OutputNameMapping]):
    figure: OutputFigure


class NameMappingProvider(StaticProvider, ABC):
    @abstractmethod
    @static_provision_action(InputNameMappingRequest)
    def _provide_input_name_mapping(self, mediator: Mediator, request: InputNameMappingRequest) -> InputNameMapping:
        pass

    @abstractmethod
    @static_provision_action(OutputNameMappingRequest)
    def _provide_output_name_mapping(self, mediator: Mediator, request: OutputNameMappingRequest) -> OutputNameMapping:
        pass
