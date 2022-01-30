from dataclasses import dataclass
from enum import Enum
from itertools import islice
from typing import List, Union, Generic, TypeVar, Dict, Callable

from .essential import Request
from .request_cls import FieldRM, TypeHintRM, InputFieldRM, ParamKind
from ..singleton import SingletonMeta

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


@dataclass
class InputFieldsFigure:
    constructor: Callable
    fields: List[InputFieldRM]
    extra: FigureExtra

    def __post_init__(self):
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


@dataclass
class OutputFieldsFigure:
    fields: List[FieldRM]
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


# It's like tree crown
Crown = Union[FieldCrown, None, DictCrown, ListCrown]

RootCrown = Union[DictCrown, ListCrown]


class BaseFFRequest(TypeHintRM[T], Generic[T]):
    pass


class InputFFRequest(BaseFFRequest[InputFieldsFigure]):
    pass


class OutputFFRequest(BaseFFRequest[OutputFieldsFigure]):
    pass


class RootCrownRequest(TypeHintRM[RootCrown]):
    pass
