from dataclasses import dataclass, field
from typing import Any, Mapping, TypeVar

from adaptix._internal.essential import CannotProvide, Request

from ..common import Dumper, Loader, TypeHint
from ..model_tools.definitions import Accessor, Default
from ..type_tools import BaseNormType, normalize_type
from ..utils import ClassMap
from .definitions import DebugTrail

T = TypeVar('T')


@dataclass(frozen=True)
class Location:
    pass


@dataclass(frozen=True)
class TypeHintLoc(Location):
    type: TypeHint


@dataclass(frozen=True)
class FieldLoc(Location):
    name: str
    default: Default
    metadata: Mapping[Any, Any] = field(hash=False)


@dataclass(frozen=True)
class InputFieldLoc(Location):
    is_required: bool


@dataclass(frozen=True)
class OutputFieldLoc(Location):
    accessor: Accessor


@dataclass(frozen=True)
class GenericParamLoc(Location):
    pos: int


LocMap = ClassMap[Location]
LR = TypeVar('LR', bound='LocatedRequest')


@dataclass(frozen=True)
class LocatedRequest(Request[T]):
    loc_map: LocMap


@dataclass(frozen=True)
class LoaderRequest(LocatedRequest[Loader]):
    pass


@dataclass(frozen=True)
class DumperRequest(LocatedRequest[Dumper]):
    pass


def get_type_from_request(request: LocatedRequest) -> TypeHint:
    return request.loc_map.get_or_raise(TypeHintLoc, CannotProvide).type


def try_normalize_type(tp: TypeHint) -> BaseNormType:
    try:
        return normalize_type(tp)
    except ValueError:
        raise CannotProvide(f'{tp} can not be normalized')


class StrictCoercionRequest(LocatedRequest[bool]):
    pass


class DebugTrailRequest(LocatedRequest[DebugTrail]):
    pass
