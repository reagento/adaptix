from dataclasses import dataclass, replace
from typing import TypeVar

from ..common import Dumper, Loader, TypeHint
from ..model_tools import BaseField, InputField, OutputField
from ..provider.essential import CannotProvide, Request

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


def get_type_from_request(request: LocatedRequest) -> TypeHint:
    if isinstance(request.loc, TypeHintLocation):
        return request.loc.type
    raise CannotProvide


LR = TypeVar('LR', bound=LocatedRequest)


def replace_type(request: LR, tp: TypeHint) -> LR:
    return replace(request, loc=replace(request.loc, type=tp))  # type: ignore
