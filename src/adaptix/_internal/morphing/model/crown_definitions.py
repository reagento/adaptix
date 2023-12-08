from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Mapping, Sequence, TypeVar, Union

from ...common import VarTuple
from ...model_tools.definitions import BaseShape, DefaultFactory, DefaultValue, InputShape, OutputShape
from ...provider.request_cls import LocatedRequest
from ...utils import SingletonMeta

T = TypeVar('T')

CrownPathElem = Union[str, int]
CrownPath = VarTuple[CrownPathElem]  # subset of struct_path.Trail


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


@dataclass
class BaseDictCrown(Generic[T]):
    map: Mapping[str, T]


@dataclass
class BaseListCrown(Generic[T]):
    map: Sequence[T]


@dataclass
class BaseNoneCrown:
    pass


@dataclass
class BaseFieldCrown:
    id: str


BranchBaseCrown = Union[BaseDictCrown, BaseListCrown]
LeafBaseCrown = Union[BaseFieldCrown, BaseNoneCrown]
BaseCrown = Union[BranchBaseCrown, LeafBaseCrown]

# --------  Input Crown -------- #

DictExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]
ListExtraPolicy = Union[ExtraSkip, ExtraForbid]


@dataclass
class InpDictCrown(BaseDictCrown['InpCrown']):
    extra_policy: DictExtraPolicy


@dataclass
class InpListCrown(BaseListCrown['InpCrown']):
    extra_policy: ListExtraPolicy


@dataclass
class InpNoneCrown(BaseNoneCrown):
    pass


@dataclass
class InpFieldCrown(BaseFieldCrown):
    pass


BranchInpCrown = Union[InpDictCrown, InpListCrown]
LeafInpCrown = Union[InpFieldCrown, InpNoneCrown]
InpCrown = Union[BranchInpCrown, LeafInpCrown]

# --------  Output Crown -------- #

# Sieve takes source object and raw field value to determine if skip field.
# True indicates to put field, False to skip.
Sieve = Callable[[Any, Any], bool]


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


Placeholder = Union[DefaultValue, DefaultFactory]


@dataclass
class OutNoneCrown(BaseNoneCrown):
    placeholder: Placeholder


@dataclass
class OutFieldCrown(BaseFieldCrown):
    pass


BranchOutCrown = Union[OutDictCrown, OutListCrown]
LeafOutCrown = Union[OutFieldCrown, OutNoneCrown]
OutCrown = Union[BranchOutCrown, LeafOutCrown]

# --------  Name Layout -------- #


class ExtraKwargs(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class ExtraTargets:
    fields: VarTuple[str]


Saturator = Callable[[T, Mapping[str, Any]], None]
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
class BaseNameLayout:
    crown: BranchBaseCrown
    extra_move: BaseExtraMove


@dataclass(frozen=True)
class BaseNameLayoutRequest(LocatedRequest[T], Generic[T]):
    shape: BaseShape


@dataclass(frozen=True)
class InputNameLayout(BaseNameLayout):
    crown: BranchInpCrown
    extra_move: InpExtraMove


@dataclass(frozen=True)
class InputNameLayoutRequest(BaseNameLayoutRequest[InputNameLayout]):
    shape: InputShape


@dataclass(frozen=True)
class OutputNameLayout(BaseNameLayout):
    crown: BranchOutCrown
    extra_move: OutExtraMove


@dataclass(frozen=True)
class OutputNameLayoutRequest(BaseNameLayoutRequest[OutputNameLayout]):
    shape: OutputShape
