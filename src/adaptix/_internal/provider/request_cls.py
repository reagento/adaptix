from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple, TypeVar

from ..common import TypeHint
from ..datastructures import ClassMap, ImmutableStack
from ..definitions import DebugTrail
from ..model_tools.definitions import Accessor, Default
from ..type_tools import BaseNormType, normalize_type
from ..utils import pairs
from .essential import CannotProvide, Request

T = TypeVar('T')


@dataclass(frozen=True)
class Location:
    pass


@dataclass(frozen=True)
class TypeHintLoc(Location):
    type: TypeHint


@dataclass(frozen=True)
class FieldLoc(Location):
    field_id: str
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
    generic_pos: int


LocMap = ClassMap[Location]
LR = TypeVar('LR', bound='LocatedRequest')
LocStackT = TypeVar('LocStackT', bound='LocStack')


class LocStack(ImmutableStack[LocMap]):
    def replace_last(self: LocStackT, loc: LocMap) -> LocStackT:
        return self[:-1].append_with(loc)

    def add_to_last_map(self: LocStackT, *locs: Location) -> LocStackT:
        return self.replace_last(self[-1].add(*locs))


@dataclass(frozen=True)
class LocatedRequest(Request[T]):
    loc_stack: LocStack

    @property
    def last_map(self) -> LocMap:
        return self.loc_stack[-1]


def get_type_from_request(request: LocatedRequest) -> TypeHint:
    return request.last_map.get_or_raise(TypeHintLoc, CannotProvide).type


def try_normalize_type(tp: TypeHint) -> BaseNormType:
    try:
        return normalize_type(tp)
    except ValueError:
        raise CannotProvide(f'{tp} can not be normalized')


class StrictCoercionRequest(LocatedRequest[bool]):
    pass


class DebugTrailRequest(LocatedRequest[DebugTrail]):
    pass


def find_owner_with_field(stack: LocStack) -> Tuple[LocMap, LocMap]:
    for next_loc_map, prev_loc_map in pairs(reversed(stack)):
        if next_loc_map.has(FieldLoc):
            return prev_loc_map, next_loc_map
    raise ValueError
