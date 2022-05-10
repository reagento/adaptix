from dataclasses import dataclass
from typing import TypeVar, Generic, Dict, List, Union, Collection, Callable, Any, Set

from dataclass_factory_30.provider import DefaultValue, DefaultFactory
from dataclass_factory_30.utils import SingletonMeta

T = TypeVar('T')

FldPathElem = Union[str, int]

# Policies how to process extra data

class ExtraSkip(metaclass=SingletonMeta):
    """Ignore any extra data"""


class ExtraForbid(metaclass=SingletonMeta):
    """Raise error if extra data would be met"""


class ExtraCollect(metaclass=SingletonMeta):
    """Collect extra data and pass it to constructor"""


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


#############################################

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

#############################################


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
