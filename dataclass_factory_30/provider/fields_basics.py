from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from typing import List, Union, Generic, TypeVar, Dict, Callable, Tuple

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
    fields: List[str]


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


# Crown defines how external structure
# should be mapped to constructor fields
# and defines the policy of extra data processing.
# None means that item of dict or list maps to nothing.
# This structure is named in honor of the crown of the tree
Crown = Union[FieldCrown, None, DictCrown, ListCrown]

RootCrown = Union[DictCrown, ListCrown]


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
class BaseCrownRequest(TypeHintRM[RootCrown]):
    figure: BaseFieldsFigure


@dataclass(frozen=True)
class InputCrownRequest(BaseCrownRequest):
    figure: InputFieldsFigure


@dataclass(frozen=True)
class OutputCrownRequest(BaseCrownRequest):
    figure: OutputFieldsFigure


class BaseCrownProvider(StaticProvider, ABC):
    @abstractmethod
    @static_provision_action(BaseCrownRequest)
    def _provide_crown(self, mediator: Mediator, request: BaseCrownRequest) -> RootCrown:
        pass


class AsIsCrownProvider(BaseCrownProvider):
    def _provide_crown(self, mediator: Mediator, request: BaseCrownRequest) -> RootCrown:
        extra_policy: ExtraPolicy = mediator.provide(CfgExtraPolicy())

        return DictCrown(
            map={
                field.field_name: FieldCrown(field.field_name)
                for field in request.figure.fields
            },
            extra=extra_policy,
        )
