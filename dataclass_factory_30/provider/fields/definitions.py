from dataclasses import dataclass
from typing import Union, Generic, TypeVar, Dict, Callable, Tuple, Collection, Any, List

from ..definitions import DefaultValue, DefaultFactory
from ..request_cls import FieldRM, TypeHintRM, InputFieldRM, ParamKind, OutputFieldRM
from ...utils import SingletonMeta, pairs

T = TypeVar('T')


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


#  =======================
#       Base Fields
#  =======================

BaseFigureExtra = Union[None, ExtraKwargs, ExtraTargets]


@dataclass(frozen=True)
class BaseFieldsFigure:
    fields: Tuple[FieldRM, ...]
    extra: BaseFigureExtra

    def _validate(self):
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

    def __post_init__(self):
        self._validate()


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
    skipped_extra_targets: Collection[str]


@dataclass(frozen=True)
class BaseFFRequest(TypeHintRM[T], Generic[T]):
    pass


@dataclass(frozen=True)
class BaseNameMappingRequest(TypeHintRM[T], Generic[T]):
    figure: BaseFieldsFigure


#  =======================
#       Input Fields
#  =======================


InpFigureExtra = Union[None, ExtraKwargs, ExtraTargets]


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
    extra: InpFigureExtra
    constructor: Callable

    def _validate(self):
        for past, current in pairs(self.fields):
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

        super()._validate()


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


InpCrown = Union[InpFieldCrown, InpNoneCrown, InpDictCrown, InpListCrown]


@dataclass
class InpNameMapping(BaseNameMapping):
    crown: Union[InpDictCrown, InpListCrown]


@dataclass(frozen=True)
class InputFFRequest(BaseFFRequest[InputFieldsFigure]):
    pass


@dataclass(frozen=True)
class InputNameMappingRequest(BaseNameMappingRequest[InpNameMapping]):
    figure: InputFieldsFigure


#  =======================
#       Output Fields
#  =======================


OutFigureExtra = BaseFigureExtra


@dataclass(frozen=True)
class OutputFieldsFigure(BaseFieldsFigure):
    fields: Tuple[OutputFieldRM, ...]
    extra: OutFigureExtra


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


@dataclass
class OutNameMapping(BaseNameMapping):
    crown: Union[OutDictCrown, OutListCrown]


@dataclass(frozen=True)
class OutputFFRequest(BaseFFRequest[OutputFieldsFigure]):
    pass


@dataclass(frozen=True)
class OutputNameMappingRequest(BaseNameMappingRequest[OutNameMapping]):
    figure: OutputFieldsFigure



DATA = {
    'a1': {
        'b1': BaseFieldCrown("field"),
        'b2': 2,
    },
    'a2': {

    }
}

RESULT = {
    'field': 0,
}
