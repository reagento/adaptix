from dataclasses import dataclass
from typing import Union, Generic, TypeVar, Dict, Callable, Tuple, Collection, Any, List, Mapping

from ..definitions import DefaultValue, DefaultFactory
from ..request_cls import FieldRM, TypeHintRM, InputFieldRM, ParamKind, OutputFieldRM
from ...common import VarTuple
from ...utils import SingletonMeta, pairs

T = TypeVar('T')


class ExtraKwargs(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class ExtraTargets:
    fields: VarTuple[str]


@dataclass(frozen=True)
class ExtraSaturate(Generic[T]):
    func: Callable[[T, Mapping[str, Any]], None]


@dataclass(frozen=True)
class ExtraExtract(Generic[T]):
    func: Callable[[Mapping[str, Any], T], Mapping[str, Any]]


#  =======================
#       Base Fields
#  =======================

BaseFigureExtra = Union[None, ExtraKwargs, ExtraTargets, ExtraSaturate[T], ExtraExtract[T]]


@dataclass(frozen=True)
class BaseFigure:
    fields: VarTuple[FieldRM]
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


InpFigureExtra = Union[None, ExtraKwargs, ExtraTargets, ExtraSaturate[T]]


@dataclass(frozen=True)
class InputFigure(BaseFigure, Generic[T]):
    """InputFigure describes how to create desired object.
    `constructor` field contains a callable that produces an instance of the class.
    `fields` field contains parameters of the constructor.

    `extra` field contains the way of passing extra data (data that does not map to any field)
    None means that constructor can not take any extra data.
    ExtraKwargs means that all extra data could be passed as additional keyword parameters
    ExtraTargets means that all extra data could be passed to corresponding fields.
    ExtraSaturate means that after constructing object specified function will be applied
    """
    fields: VarTuple[InputFieldRM]
    extra: InpFigureExtra[T]
    constructor: Callable[..., T]

    def _validate(self):
        for past, current in pairs(self.fields):
            if past.param_kind.value > current.param_kind.value:
                raise ValueError(
                    f"Inconsistent order of fields,"
                    f" {current.param_kind} must be after {past.param_kind}"
                )

            if (
                past.is_optional
                and current.is_required
                and current.param_kind != ParamKind.KW_ONLY
            ):
                raise ValueError(
                    f"All not required fields must be after required ones"
                    f" except {ParamKind.KW_ONLY} fields"
                )

        super()._validate()


OutFigureExtra = Union[None, ExtraTargets, ExtraExtract[T]]


@dataclass(frozen=True)
class OutputFigure(BaseFigure):
    fields: VarTuple[OutputFieldRM]
    extra: OutFigureExtra
