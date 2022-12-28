from dataclasses import dataclass
from typing import TypeVar

from ..common import Dumper, Loader, TypeHint
from ..model_tools import BaseField, InputField, OutputField
from .essential import Request

T = TypeVar('T')


@dataclass(frozen=True)
class Location:
    pass


@dataclass(frozen=True)
class TypeHintLocation(Location):
    type: TypeHint


@dataclass(frozen=True)
class FieldLocation(BaseField, TypeHintLocation):
    pass


@dataclass(frozen=True)
class InputFieldLocation(InputField, FieldLocation):
    pass


@dataclass(frozen=True)
class OutputFieldLocation(OutputField, FieldLocation):
    pass


@dataclass(frozen=True)
class LocatedRequest(Request[T]):
    loc: Location


@dataclass(frozen=True)
class LoaderRequest(LocatedRequest[Loader]):
    strict_coercion: bool
    debug_path: bool


@dataclass(frozen=True)
class DumperRequest(LocatedRequest[Dumper]):
    debug_path: bool
